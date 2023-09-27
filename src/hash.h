#if defined(__i386__) || defined(__x86_64__)
#include <immintrin.h>
#else
#include "sse2neon.h"
#endif

#include "spooky.h"
#include "types.h"

typedef uint32_t (*hash_fn_t)(uint32_t seed, intkey_t key);

uint32_t
hash_crc(uint32_t seed, intkey_t key);

uint32_t
hash_FNV(uint32_t seed, intkey_t key);

uint32_t
hash_crapwow(uint32_t seed, intkey_t key);

uint32_t
hash_Coffin(uint32_t seed, intkey_t key);

uint32_t
hash_MurmurOAAT_32(uint32_t seed, intkey_t key);

uint32_t
hash_JenkinsOAAT_32(uint32_t seed, intkey_t key);

uint32_t
hash_Spooky(uint32_t seed, intkey_t key);

uint32_t
hash_KR_v2(uint32_t seed, intkey_t key);

uint32_t
hash_DJB2(uint32_t seed, intkey_t key);

uint32_t
hash_x17(uint32_t seed, intkey_t key);
