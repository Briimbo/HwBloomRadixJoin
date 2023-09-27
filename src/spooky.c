// Spooky Hash
// A 128-bit noncryptographic hash, for checksums and table lookup
// By Bob Jenkins.  Public domain.
// Adapted from https://burtleburtle.net/bob/c/spooky.cpp

#include <memory.h>

#include "spooky.h"

//
// short hash ... it could be used on any message,
// but it's used by Spooky just for short messages.
//
void
Short(intkey_t message, uint64_t * hash1, uint64_t * hash2)
{
    uint64_t c = sc_const + message;
    uint64_t d = ((uint64_t) sizeof(intkey_t)) << 56;
    ShortEnd(hash1, hash2, &c, &d);
}

void
hash_spooky128(intkey_t message, uint64_t * hash1, uint64_t * hash2)
{
    Short(message, hash1, hash2);
    return;
}

uint64_t
hash_spooky64(intkey_t message, uint64_t seed)
{
    uint64_t hash1 = seed;
    hash_spooky128(message, &hash1, &seed);
    return hash1;
}

uint32_t
hash_spooky32(intkey_t message, uint32_t seed)
{
    uint64_t hash1 = seed, hash2 = seed;
    hash_spooky128(message, &hash1, &hash2);
    return (uint32_t) hash1;
}