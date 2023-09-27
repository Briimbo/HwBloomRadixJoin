#ifndef BLOOM_FILTER_H
#define BLOOM_FILTER_H

#include <stdbool.h>
#include <stdint.h>

#include "lock.h"
#include "types.h"

typedef enum { BASIC, BLOCKED } bloom_filter_variant_t;

typedef struct bloom_filter_t {
    bloom_filter_variant_t variant; /* the type of filter */
    unsigned char *        bitmap;  /* filter entries */
    uint32_t               seed;    /* random seed */
    uint64_t               m; /* filter size in bits (must be multiple of 8) */
    uint64_t               k; /* number of hash functions to use */
    uint64_t               B; /* block size in bits (must be multiple of 8) */
    uint64_t               nblocks; /* number of blocks in filter (m/B) */
} bloom_filter_t;

/**
 * @brief Adds the key to the bloom filter
 *
 * @param bloom_filter the filter that the key should be inserted to
 * @param key the key to be inserted
 */
typedef void (*bloom_filter_add_strategy_t)(const bloom_filter_t * filter,
                                            const intkey_t         key);

/**
 * @brief checks if the bloom filter possibly contains an element (key)
 *
 * @param bloom_filter The filter to be checked
 * @param key The key to be searched for
 * @return true if the element might be present. Note that this does not mean
 * that it is definitely present!
 * @return false if the element is definitely not present
 */
typedef bool (*bloom_filter_contains_strategy_t)(const bloom_filter_t * filter,
                                                 const intkey_t         key);

typedef struct bloom_filter_strategy_t {
    bloom_filter_variant_t           variant;
    bloom_filter_t *                 filter;
    bloom_filter_add_strategy_t      add;
    bloom_filter_contains_strategy_t contains;
} bloom_filter_strategy_t;

typedef struct bloom_filter_args_t {
    bloom_filter_variant_t variant; /* the type of filter */
    uint64_t               m; /* filter size in bits (must be multiple of 8) */
    uint64_t               k; /* number of hash functions to use */
    uint64_t               B; /* block size in bits (must be multiple of 8) */
} bloom_filter_args_t;

typedef enum { INSERT, CHECK, IGNORE } bloom_filter_usage_t;

/**
 * Creates and initializes a bloom filter given the necessary parameters
 *
 * @param m the number of entries in the filter (bitmap size)
 * @param k the number of entries to be set per inserted tuple
 * @param seed random seed to be used for hash function
 *
 * @return The initialized bloom filter
 */
bloom_filter_strategy_t *
bloom_filter_create(bloom_filter_args_t * args, uint32_t seed);

/**
 * @brief Frees the space occupied by the bloom filter
 *
 * @param bloom_filter the bloom filter to be freed
 */
void
bloom_filter_destroy(bloom_filter_strategy_t * bloom_filter_strategy);

void
assert_args(bloom_filter_args_t * args);

#endif
