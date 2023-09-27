#if defined(__i386__) || defined(__x86_64__)
#include <immintrin.h>
#else
#include "sse2neon.h"
#endif
#include <math.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "bloom_filter.h"
#include "hash.h"
#include "prj_params.h"

static inline void
assert(bool cond, char * msg)
{
    if (!cond) {
        printf(msg);
        exit(1);
    }
}

void
assert_args(bloom_filter_args_t * args)
{
    assert((args->m & (args->m - 1)) == 0, "m must be a power of 2");

    if (args->variant != BASIC) {
        assert(pow(2, (int) log2(args->B)) == args->B, "B must be a power 2");
        assert(args->m % args->B == 0, "m must be a multiple of B");
    }
}

static void *
calloc_aligned(size_t size)
{
    void * ret;
    int    rv;
    rv = posix_memalign((void **) &ret, CACHE_LINE_SIZE, size);

    if (rv) {
        perror("alloc_aligned() failed: out of memory");
        return 0;
    }
    memset(ret, 0, size);

    return ret;
}

/**
 * @brief Compute mod_m for m which is a power of 2, i.e. m = 2^x
 *
 * @param val the value to be taken modulo
 * @param m the modulo operant, must be a power of 2
 * @return the resulting value in the range of 0 to m-1
 */
static inline uint32_t
mod_m(uint32_t val, uint64_t m)
{
    return val & (m - 1);
}

/**
 * @brief generic method to add a key to a filter
 *
 * @param filter the filter to add the key to
 * @param key the key to add
 * @param bitmap the bitmap to set the bits in, separated to support blocked filters
 * @param size the size of the filter, separated to support blocked filters
 */
void
add_generic(const bloom_filter_t * filter, const intkey_t key,
            unsigned char * bitmap, uint32_t size)
{
    uint32_t h = hash_crapwow(filter->seed, key);
    uint32_t y = key + filter->seed;

    h = mod_m(h, size);
    y = mod_m(y, size);

    for (int i = 0; i < filter->k; i++) {
        atomic_fetch_or_explicit(bitmap + (h >> 3), 1 << (h & 7),
                                 memory_order_relaxed);
        h = mod_m(h + y, size);
        y = mod_m(y + i + 1, size);
    }
}

// separate bitmap and size from filter param to simultaneously support basic and blocked filter
bool
contains_generic(const bloom_filter_t * filter, const intkey_t key,
                 const unsigned char * bitmap, uint32_t size)
{
    uint32_t h = hash_crapwow(filter->seed, key);
    uint32_t y = key + filter->seed;

    h = mod_m(h, size);
    y = mod_m(y, size);

    for (int i = 0; i < filter->k; i++) {
        if (!(bitmap[h >> 3] & (1 << (h & 7)))) {
            return false;
        }

        h = mod_m(h + y, size);
        y = mod_m(y + i + 1, size);
    }
    return true;
}

void
add_basic(const bloom_filter_t * filter, const intkey_t key)
{
    add_generic(filter, key, filter->bitmap, filter->m);
}

bool
contains_basic(const bloom_filter_t * filter, const intkey_t key)
{
    return contains_generic(filter, key, filter->bitmap, filter->m);
}

void
add_blocked(const bloom_filter_t * filter, const intkey_t key)
{
    uint32_t block_idx    = mod_m(hash_crc(filter->seed, key), filter->nblocks);
    unsigned char * block = filter->bitmap + block_idx * (filter->B / 8);

    add_generic(filter, key, block, filter->B);
}

bool
contains_blocked(const bloom_filter_t * filter, const intkey_t key)
{
    uint32_t block_idx    = mod_m(hash_crc(filter->seed, key), filter->nblocks);
    unsigned char * block = filter->bitmap + block_idx * (filter->B / 8);

    return contains_generic(filter, key, block, filter->B);
}

bloom_filter_strategy_t *
bloom_filter_create(bloom_filter_args_t * args, uint32_t seed)
{
    bloom_filter_strategy_t * strategy = malloc(sizeof(bloom_filter_strategy_t));
    bloom_filter_t *          filter   = malloc(sizeof(bloom_filter_t));

    filter->variant = args->variant;
    filter->m       = args->m;
    filter->k       = args->k;
    filter->B       = args->B;
    filter->nblocks = args->m / args->B;
    filter->seed    = seed;
    filter->bitmap  = calloc_aligned(args->m / 8);

    strategy->variant = args->variant;
    strategy->filter  = filter;

    switch (args->variant) {
        case BASIC:
            strategy->add      = add_basic;
            strategy->contains = contains_basic;
            break;
        case BLOCKED:
            strategy->add      = add_blocked;
            strategy->contains = contains_blocked;
            break;
    }
    return strategy;
}

void
bloom_filter_destroy(bloom_filter_strategy_t * strategy)
{
    free(strategy->filter->bitmap);
    free(strategy->filter);
    free(strategy);
}
