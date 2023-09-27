//
// SpookyHash: a 128-bit noncryptographic hash function
// By Bob Jenkins, public domain
// Adapted from https://burtleburtle.net/bob/c/spooky.h

#ifndef SPOOKY_H
#define SPOOKY_H

#include <stddef.h>
#include <stdint.h>

#include "types.h"

//
// SpookyHash: hash a single message in one call, produce 128-bit output
//
void
hash_spooky128(intkey_t   message,  // message to hash
               uint64_t * hash1,    // in/out: in seed 1, out hash value 1
               uint64_t * hash2);   // in/out: in seed 2, out hash value 2

uint64_t
hash_spooky64(intkey_t message,  // message to hash
              uint64_t seed);    // seed

//
// Hash32: hash a single message in one call, produce 32-bit output
//
uint32_t
hash_spooky32(intkey_t message,  // message to hash
              uint32_t seed);    // seed

//
// left rotate a 64-bit value by k bytes
//
static inline uint64_t
Rot64(uint64_t x, int k)
{
    return (x << k) | (x >> (64 - k));
}

//
// The goal is for each bit of the input to expand into 128 bits of
//   apparent entropy before it is fully overwritten.
// n trials both set and cleared at least m bits of h0 h1 h2 h3
//   n: 2   m: 29
//   n: 3   m: 46
//   n: 4   m: 57
//   n: 5   m: 107
//   n: 6   m: 146
//   n: 7   m: 152
// when run forwards or backwards
// for all 1-bit and 2-bit diffs
// with diffs defined by either xor or subtraction
// with a base of all zeros plus a counter, or plus another bit, or random
//
static inline void
ShortMix(uint64_t * h0, uint64_t * h1, uint64_t * h2, uint64_t * h3)
{
    *h2 = Rot64(*h2, 50);
    *h2 += *h3;
    *h0 ^= *h2;
    *h3 = Rot64(*h3, 52);
    *h3 += *h0;
    *h1 ^= *h3;
    *h0 = Rot64(*h0, 30);
    *h0 += *h1;
    *h2 ^= *h0;
    *h1 = Rot64(*h1, 41);
    *h1 += *h2;
    *h3 ^= *h1;
    *h2 = Rot64(*h2, 54);
    *h2 += *h3;
    *h0 ^= *h2;
    *h3 = Rot64(*h3, 48);
    *h3 += *h0;
    *h1 ^= *h3;
    *h0 = Rot64(*h0, 38);
    *h0 += *h1;
    *h2 ^= *h0;
    *h1 = Rot64(*h1, 37);
    *h1 += *h2;
    *h3 ^= *h1;
    *h2 = Rot64(*h2, 62);
    *h2 += *h3;
    *h0 ^= *h2;
    *h3 = Rot64(*h3, 34);
    *h3 += *h0;
    *h1 ^= *h3;
    *h0 = Rot64(*h0, 5);
    *h0 += *h1;
    *h2 ^= *h0;
    *h1 = Rot64(*h1, 36);
    *h1 += *h2;
    *h3 ^= *h1;
}

//
// Mix all 4 inputs together so that h0, h1 are a hash of them all.
//
// For two inputs differing in just the input bits
// Where "differ" means xor or subtraction
// And the base value is random, or a counting value starting at that bit
// The final result will have each bit of h0, h1 flip
// For every input bit,
// with probability 50 +- .3% (it is probably better than that)
// For every pair of input bits,
// with probability 50 +- .75% (the worst case is approximately that)
//
static inline void
ShortEnd(uint64_t * h0, uint64_t * h1, uint64_t * h2, uint64_t * h3)
{
    *h3 ^= *h2;
    *h2 = Rot64(*h2, 15);
    *h3 += *h2;
    *h0 ^= *h3;
    *h3 = Rot64(*h3, 52);
    *h0 += *h3;
    *h1 ^= *h0;
    *h0 = Rot64(*h0, 26);
    *h1 += *h0;
    *h2 ^= *h1;
    *h1 = Rot64(*h1, 51);
    *h2 += *h1;
    *h3 ^= *h2;
    *h2 = Rot64(*h2, 28);
    *h3 += *h2;
    *h0 ^= *h3;
    *h3 = Rot64(*h3, 9);
    *h0 += *h3;
    *h1 ^= *h0;
    *h0 = Rot64(*h0, 47);
    *h1 += *h0;
    *h2 ^= *h1;
    *h1 = Rot64(*h1, 54);
    *h2 += *h1;
    *h3 ^= *h2;
    *h2 = Rot64(*h2, 32);
    *h3 += *h2;
    *h0 ^= *h3;
    *h3 = Rot64(*h3, 25);
    *h0 += *h3;
    *h1 ^= *h0;
    *h0 = Rot64(*h0, 63);
    *h1 += *h0;
}

//
// Short is used for messages under 192 bytes in length
// Short has a low startup cost, the normal mode is good for long
// keys, the cost crossover is at about 192 bytes.  The two modes were
// held to the same quality bar.
//
void
Short(intkey_t   message,  // message (array of bytes, not necessarily aligned)
      uint64_t * hash1,    // in/out: in the seed, out the hash value
      uint64_t * hash2);   // in/out: in the seed, out the hash value

//
// sc_const: a constant which:
//  * is not zero
//  * is odd
//  * is a not-very-regular mix of 1's and 0's
//  * does not need any other special mathematical properties
//
static const uint64_t sc_const = 0xdeadbeefdeadbeefLL;

#endif