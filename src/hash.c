#include "hash.h"

/* We need different, independent hash functions. Most of these functions are adapted from
 * https://stackoverflow.com/questions/7666509/hash-function-for-string */

uint32_t
hash_crc(uint32_t seed, intkey_t key)
{
    return _mm_crc32_u32(seed, key);
}

uint32_t
hash_FNV(uint32_t seed, intkey_t key)
{
    //  Source: https://github.com/aappleby/smhasher/blob/master/src/Hashes.cpp
    uint32_t h = seed;
    h ^= 2166136261UL;
    for (int i = 0; i < sizeof(intkey_t); i++) {
        char byte = (key >> (i * 8)) & 0xFF;
        h ^= byte;
        h *= 16777619;
    }
    return h;
}

// Source https://web.archive.org/web/20150531125306/http://floodyberry.com/noncryptohashzoo/CrapWow.html
#define cwfold(a, b, lo, hi)         \
{                                    \
p = (uint32_t) (a) * (uint64_t) (b); \
lo ^= (uint32_t) p;                  \
hi ^= (uint32_t) (p >> 32);          \
}
#define cwmixb(in) cwfold(in, n, h, k)

uint32_t
hash_crapwow(uint32_t seed, intkey_t key)
{
    // Source https://web.archive.org/web/20150531125306/http://floodyberry.com/noncryptohashzoo/CrapWow.html
    uint32_t n = 0x5052acdb;
    uint32_t h = sizeof(intkey_t);
    uint32_t k = h + seed + n;
    uint64_t p;

    cwmixb(key);
    cwmixb(h ^ (k + n));
    return k ^ h;
}

static inline uint32_t
_rotl32(uint32_t x, int32_t bits)
{
    return x << bits | x >> (32 - bits);
}

uint32_t
hash_Coffin(uint32_t seed, intkey_t key)
{
    // Source: https://stackoverflow.com/a/7666668/5407270
    uint32_t result = 0x55555555;
    for (int i = 0; i < sizeof(intkey_t); i++) {
        char byte = (key >> (i * 8)) & 0xFF;
        result ^= byte;
        result = _rotl32(result, 5);
    }
    return result;
}

uint32_t
hash_MurmurOAAT_32(uint32_t seed, intkey_t key)
{
    // One-byte-at-a-time hash based on Murmur's mix
    // Source: https://github.com/aappleby/smhasher/blob/master/src/Hashes.cpp
    uint32_t h = seed;
    for (int i = 0; i < sizeof(intkey_t); i++) {
        char byte = (key >> (i * 8)) & 0xFF;
        h ^= byte;
        h *= 0x5bd1e995;
        h ^= h >> 15;
    }
    return h;
}

uint32_t
hash_JenkinsOAAT_32(uint32_t seed, intkey_t key)
{
    // Source: https://burtleburtle.net/bob/hash/doobs.html#one
    uint32_t h = seed;
    for (int i = 0; i < sizeof(intkey_t); i++) {
        char byte = (key >> (i * 8)) & 0xFF;
        h += byte;
        h += (h << 10);
        h ^= (h >> 6);
    }

    h += (h << 3);
    h ^= (h >> 11);
    h += (h << 15);
    return h;
}

uint32_t
hash_Spooky(uint32_t seed, intkey_t key)
{
    return hash_spooky32(key, seed);
}

uint32_t
hash_KR_v2(uint32_t seed, intkey_t key)
{
    // Source: https://stackoverflow.com/a/45641002/5407270
    uint32_t h = seed;
    for (int i = 0; i < sizeof(intkey_t); i++) {
        char byte = (key >> (i * 8)) & 0xFF;
        h         = byte + 31 * h;
    }
    return h;
}

uint32_t
hash_DJB2(uint32_t seed, intkey_t key)
{
    // Source: https://stackoverflow.com/a/7666577
    uint32_t hash = 5381;
    for (int i = 0; i < sizeof(intkey_t); i++) {
        char byte = (key >> (i * 8)) & 0xFF;
        hash      = ((hash << 5) + hash) + byte; /* hash * 33 + c */
    }
    return hash;
}

uint32_t
hash_x17(uint32_t seed, intkey_t key)
{
    // Source: https://github.com/aappleby/smhasher/blob/master/src/Hashes.cpp
    uint32_t h = seed;
    for (int i = 0; i < sizeof(intkey_t); i++) {
        char byte = (key >> (i * 8)) & 0xFF;
        h         = 17 * h + (byte - ' ');
    }
    return h ^ (h >> 16);
}