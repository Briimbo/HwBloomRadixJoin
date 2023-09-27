#define _GNU_SOURCE
#include <math.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/time.h>
#include <time.h>

#include "bloom_filter.h"
#include "fort.h"
#include "generator.h"
#include "hash.h"
#include "rdtsc.h"

static inline void
assert(bool cond, char * msg, ...)
{
    va_list args;
    va_start(args, msg);
    if (!cond) {
        vfprintf(stderr, msg, args);
    }
    va_end(args);
}

static inline uint32_t
mod_m(uint32_t val, uint64_t m)
{
    return val & (m - 1);
}

/**
 * @brief test hash function speed and collisions
 * Collisions are computed for full uint32 range.
 *
 * @param seed seed to initialize hashed values
 * @param n_samples number of samples to compute values for
 */
void
test_hash(int seed, uint32_t n_samples)
{
    srand(seed);
    uint32_t *          inputs  = malloc(n_samples * sizeof(uint32_t));
    volatile uint32_t * outputs = malloc(n_samples * sizeof(uint32_t));

    FILE * outstream = stdout;
    fprintf(
        outstream,
        "algorithm;time_total_ms;time_single_ns;collisions;collisions_pct\n");

    hash_fn_t hash_fns[10] = {hash_crc,           hash_FNV,
                              hash_crapwow,       hash_Coffin,
                              hash_MurmurOAAT_32, hash_JenkinsOAAT_32,
                              hash_Spooky,        hash_KR_v2,
                              hash_DJB2,          hash_x17};

    char * names[10] = {"crc",        "FNV",           "crapwow",
                        "Coffin",     "MurmurOAAT_32", "JenkinsOAAT_32",
                        "SpookyHash", "KR_v2",         "DJB2",
                        "x17"};

    for (int i = 0; i < n_samples; i++) {
        inputs[i] = rand();
    }

    char * in_duplicates = calloc(UINT32_MAX, sizeof(char));
    for (int i = 0; i < n_samples; i++) {
        in_duplicates[inputs[i]] += 1;
    }
    uint32_t in_collisions = 0;
    for (uint32_t j = 0; j < UINT32_MAX; j++) {
        if (in_duplicates[j] > 1) {
            in_collisions += in_duplicates[j] - 1;
        }
    }

    for (int i = 0; i < 10; i++) {
        /* timing */
        struct timeval start, end;
        hash_fn_t      hash = hash_fns[i];
        gettimeofday(&start, NULL);
        for (int j = 0; j < n_samples; j++) {
            outputs[j] = hash(seed, inputs[j]);
        }
        gettimeofday(&end, NULL);

        /* collisions */
        char * hit_counts = calloc(UINT32_MAX, sizeof(char));
        for (int j = 0; j < n_samples; j++) {
            uint32_t idx = hash(seed, inputs[j]);
            hit_counts[idx] += 1;
        }

        uint32_t collisions = 0;
        for (uint32_t j = 0; j < UINT32_MAX; j++) {
            if (hit_counts[j] > 1) {
                collisions += hit_counts[j] - 1;
            }
        }
        collisions -= in_collisions;

        uint64_t diff = (end.tv_sec - start.tv_sec) * 1000000 + end.tv_usec
                        - start.tv_usec;

        fprintf(outstream, "%s;%.2f;%.2f;%d;%.2f\n", names[i], diff / 1000.0,
                (diff / (float) n_samples) * 1000, collisions,
                collisions / (float) n_samples * 100);

        free(hit_counts);
    }

    fflush(outstream);

    free(inputs);
    free(outputs);
}

void
test_enhanced_double_hashing(int seed, uint32_t n_samples)
{
    srand(seed);
    uint32_t     h = rand();
    uint32_t     y = rand();
    uint32_t     m = 2 << 20;
    unsigned int k = 100;

    struct timeval start, end;
    uint64_t       timer;
    gettimeofday(&start, NULL);
    startTimer(&timer);
    for (uint32_t j = 0; j < n_samples; j++) {
        h = mod_m(h, m);
        y = mod_m(y, m);

        for (uint32_t i = 0; i < k; i++) {
            h = mod_m(h + y, m);
            y = mod_m(y + i + 1, m);
        }
    }
    stopTimer(&timer);
    gettimeofday(&end, NULL);

    fprintf(stdout, "h: %d, y: %d\n", h, y);
    uint64_t diff = (end.tv_sec - start.tv_sec) * 1000000 + end.tv_usec
                    - start.tv_usec;
    float ns_per_hash     = diff * 1000.0 / n_samples / k;
    float cycles_per_hash = timer / (float) n_samples / k;
    fprintf(stdout, "ns_per_hash;%.4f;cycles_per_hash;%.4f", ns_per_hash,
            cycles_per_hash);
    fflush(stdout);
}

// using knuth algorithm, see https://stackoverflow.com/a/1608585
void
random_unique_gen_range(relation_t * R, intkey_t min, intkey_t max)
{
    uint64_t  n         = R->num_tuples;
    tuple_t * arr       = R->tuples;
    uint32_t  inserted  = 0;
    intkey_t  m_options = max - min;
    assert(m_options >= n,
           "range need to be larger (>=) than number of desired elements");

    for (uint32_t i = 0; i < m_options && inserted < n; ++i) {
        int rn = n - inserted;
        int rm = m_options - i;
        if (rand() % rm < rn) {
            arr[inserted].key     = min + i;
            arr[inserted].payload = min + i;
            inserted++;
        }
    }
}

/**
 * @brief Test the effects of a specific k, i.e. measures the accuracy (FPR) and
 * runtime. The runtime is is expected to increase for increasing k. The
 * accuracy should increase (FPR decrease) for increasing k up to a sweet spot
 * at k = ln(2) * m/n. The expected FPR can be calculated for basic bloom
 * filters. While blocked bloom filters behave differently, the FPR can still be
 * (under)approximated with the expected FPR of a basic bloom filter.
 *
 * @param table table to output results
 * @param seed seed for RNG, i.e. generate BF seed
 * @param m bloom filter m (size)
 * @param k bloom filter k
 * @param variant bloom filter type
 * @param R tuples to insert, must be non-overlapping with S!
 * @param S tuples to probe the bloom filter for, must be non-overlapping with R!
 */
void
test_bloom_fpr(ft_table_t * table, uint32_t seed, uint64_t m, uint64_t k,
               bloom_filter_variant_t variant, relation_t * R, relation_t * S)
{
    srand(seed);
    bloom_filter_args_t args;
    args.m                                 = m;
    args.k                                 = k;
    args.variant                           = variant;
    args.B                                 = 512;
    bloom_filter_strategy_t * filter_strat = bloom_filter_create(&args, rand());
    bloom_filter_t *          filter       = filter_strat->filter;

    double   selectivity  = 0;
    uint64_t n_insertions = R->num_tuples;
    uint64_t n_samples    = S->num_tuples;

    clock_t start_add = clock();
    for (uint32_t i = 0; i < n_insertions; i++) {
        filter_strat->add(filter, R->tuples[i].key);
    }
    clock_t end_add = clock();

    uint32_t pos            = 0;
    clock_t  start_contains = clock();
    for (uint32_t i = 0; i < n_samples; i++) {
        pos += filter_strat->contains(filter, S->tuples[i].key);
    }
    clock_t end_contains = clock();

    uint32_t neg = n_samples * (1 - selectivity);
    uint32_t tp  = n_samples - neg;
    uint32_t fp  = pos - tp;
    double   fpr = fp / ((double) neg);

    bloom_filter_destroy(filter_strat);

    char *k_str, *real_fpr, *expected_fpr, *time_add, *time_contains;
    asprintf(&k_str, "%lu", k);
    asprintf(&real_fpr, "%.3f%%", fpr * 100);
    asprintf(&expected_fpr, "%.3f%%",
             pow(1 - pow(1 - 1 / (double) m, k * n_insertions), k) * 100);
    asprintf(&time_add, "%.4f",
             (end_add - start_add) / (float) n_insertions / k * 1000000.0);
    asprintf(&time_contains, "%.4f",
             (end_contains - start_contains) / (float) n_samples * 1000000.0);

    ft_write_ln(table, "", "", "", "", k_str, real_fpr, expected_fpr, time_add,
                time_contains);
}

void
test_bloom_fpr_wrapper(int seed, uint64_t m, uint64_t k_max, uint32_t n_samples,
                       uint32_t n_insertions)
{
    srand(seed + 1);

    ft_table_t * table;
    table = ft_create_table();
    ft_set_cell_prop(table, 0, FT_ANY_COLUMN, FT_CPROP_ROW_TYPE, FT_ROW_HEADER);
    ft_write_ln(table, "bloom-size", "r-size", "s-size", "bloom-filter",
                "bloom-hashes", "fpr_emp", "fpr_theo", "time (us) add per k",
                "time (us) contains total");
    char *m_str, *r_str, *s_str;
    asprintf(&m_str, "%u", m);
    asprintf(&r_str, "%u", n_insertions);
    asprintf(&s_str, "%u", n_samples);

    relation_t R, S;
    R.tuples     = malloc(n_insertions * sizeof(tuple_t));
    R.num_tuples = n_insertions;
    S.tuples     = malloc(n_samples * sizeof(tuple_t));
    S.num_tuples = n_samples;

    intkey_t threshold = INT32_MAX
                         * (n_insertions / (double) (n_insertions + n_samples));
    random_unique_gen_range(&R, 0, threshold);
    random_unique_gen_range(&S, threshold + 1, INT32_MAX);

    ft_write_ln(table, m_str, r_str, s_str, "blocked", "", "", "", "", "");
    for (int k = 1; k <= k_max; k += 1) {
        test_bloom_fpr(table, seed, m, k, BLOCKED, &R, &S);
    }
    ft_write_ln(table, m_str, r_str, s_str, "basic", "", "", "", "", "");
    for (int k = 1; k <= k_max; k += 1) {
        test_bloom_fpr(table, seed, m, k, BASIC, &R, &S);
    }
    free(S.tuples);
    free(R.tuples);

    printf("%s\n", ft_to_string(table));
    ft_destroy_table(table);
}

/**
 * @brief Parses the input arguments and executes the unit-test-like tests
 * The parameters need to be provided in order but can be left out to use
 * default values Specifying "later" parameters need all preceeding ones to be
 * specified. The parameters are:
 * 1. Test index: 0=test_hash, 1=test_enhanced_double_hashing, 2=test_bloom_fpr
 * 2. seed: for random values
 * 3. n_samples: Number of samples for testing
 *
 * The following parameters only apply to test_bloom_fpr:
 * 4. n_insertions: number of elements to insert into the filter
 * 5. m: filter size in bits
 * 6. k_max: maximum k for the fpr test
 *
 * @param argc
 * @param argv
 * @return int
 */
int
main(int argc, char ** argv)
{
    int      seed         = 19201;
    uint64_t m            = 1024;
    uint64_t k_max        = 1;
    uint32_t n_samples    = 100000000;
    uint32_t n_insertions = 0;
    int      test_idx     = 0;
    if (argc > 1) {
        test_idx = atoi(argv[1]);
    }
    if (argc > 2) {
        seed = atoi(argv[2]);
    }
    if (argc > 3) {
        n_samples = atoi(argv[3]);
    }
    if (argc > 4) {
        n_insertions = atoi(argv[4]);
    }
    if (argc > 5) {
        m = atoi(argv[5]);
    }
    if (argc > 6) {
        k_max = atoi(argv[6]);
    }

    switch (test_idx) {
        case 0:
            test_hash(seed, n_samples);
            break;
        case 1:
            test_enhanced_double_hashing(seed, n_samples);
            break;
        case 2:
            test_bloom_fpr_wrapper(seed, m, k_max, n_samples, n_insertions);
            break;
        default:
            break;
    }
}
