/* @version $Id: cpu_mapping.c 4548 2013-12-07 16:05:16Z bcagri $ */

#include <numaif.h> /* get_mempolicy() */
#include <stdio.h>  /* FILE, fopen */
#include <stdlib.h> /* exit, perror */
#include <unistd.h> /* sysconf */

#include "cpu_mapping.h"

/** \internal
 * @{
 */

#define MAX_NODES 512

static int inited = 0;
static int max_cpus;
static int node_mapping[MAX_NODES];

/**
 * Initializes the cpu mapping from the file defined by CUSTOM_CPU_MAPPING.
 * The mapping used for our machine Intel L5520 is = "8 0 1 2 3 8 9 10 11".
 */
static int
init_mappings_from_file()
{
    FILE * cfg;
    int    i;

    cfg = fopen(CUSTOM_CPU_MAPPING, "r");
    if (cfg != NULL) {
        if (fscanf(cfg, "%d", &max_cpus) <= 0) {
            perror("Could not parse input!\n");
        }

        for (i = 0; i < max_cpus; i++) {
            if (fscanf(cfg, "%d", &node_mapping[i]) <= 0) {
                perror("Could not parse input!\n");
            }
        }

        fclose(cfg);
        return 1;
    }

    /* perror("Custom cpu mapping file not found!\n"); */
    return 0;
}

/**
 * Try custom cpu mapping file first, if does not exist then round-robin
 * initialization among available CPUs reported by the system.
 */
static void
init_mappings()
{
    if (init_mappings_from_file() == 0) {
        int i;

        max_cpus = sysconf(_SC_NPROCESSORS_ONLN);
        for (i = 0; i < max_cpus; i++) {
            node_mapping[i] = i;
        }
    }
}

/** @} */

/**
 * Returns SMT aware logical to physical CPU mapping for a given thread id.
 */
int
get_cpu_id(int thread_id)
{
    if (!inited) {
        init_mappings();
        inited = 1;
    }

    return node_mapping[thread_id % max_cpus];
}

/* TODO: These are just place-holder implementations. */
/**
 * Topology of Intel E5-4640
 node 0 cpus: 0 4 8 12 16 20 24 28 32 36 40 44 48 52 56 60
 node 1 cpus: 1 5 9 13 17 21 25 29 33 37 41 45 49 53 57 61
 node 2 cpus: 2 6 10 14 18 22 26 30 34 38 42 46 50 54 58 62
 node 3 cpus: 3 7 11 15 19 23 27 31 35 39 43 47 51 55 59 63
*/
#define INTEL_E5 0
#define INTEL_XEON_E5_2690 0
#define INTEL_XEON_E5_2697 0
#define INTEL_XEON_GOLD_6226 0
#define INTEL_XEON_GOLD_6230 0
#define INTEL_XEON_PHI_7250 0

#if INTEL_XEON_GOLD_6226
static int numa[][24] = {
    {0,  1,  2,  3,  4,  5,  6,  7,  8,  9,  10, 11,
     12, 13, 14, 15, 16, 17, 18, 29, 20, 21, 22, 23},
    {24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35,
     36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47}
};
#elif INTEL_XEON_E5_2690
static int numa[][16] = {
    {0, 1, 2,  3,  4,  5,  6,  7,  16, 17, 18, 19, 20, 21, 22, 23},
    {8, 9, 10, 11, 12, 13, 14, 15, 24, 25, 26, 27, 28, 29, 30, 31}
};
#elif INTEL_XEON_E5_2697
static int numa[][28] = {
    {0,  1,  2,  3,  4,  5,  6,  7,  8,  9,  10, 11, 12, 13,
     28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41},
    {14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27,
     42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55}
};
#elif INTEL_XEON_GOLD_6230
static int numa[][40] = {
    {0,  1,  2,  3,  4,  5,  6,  7,  8,  9,  10, 11, 12, 13,
     14, 15, 16, 17, 18, 19, 40, 41, 42, 43, 44, 45, 46, 47,
     48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59},
    {20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33,
     34, 35, 36, 37, 38, 39, 60, 61, 62, 63, 64, 65, 66, 67,
     68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79}
};
#elif INTEL_XEON_PHI_7250
static int numa[][272] = {
    {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14,
     15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
     30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44,
     45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59,
     60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74,
     75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
     90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104,
     105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119,
     120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134,
     135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149,
     150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164,
     165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179,
     180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194,
     195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209,
     210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224,
     225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239,
     240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254,
     255, 256, 257, 258, 259, 260, 261, 262, 263, 264, 265, 266, 267, 268, 269,
     270, 271}
};
#else
static int numa[][16] = {
    {0, 4, 8,  12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 60},
    {1, 5, 9,  13, 17, 21, 25, 29, 33, 37, 41, 45, 49, 53, 57, 61},
    {2, 6, 10, 14, 18, 22, 26, 30, 34, 38, 42, 46, 50, 54, 58, 62},
    {3, 7, 11, 15, 19, 23, 27, 31, 35, 39, 43, 47, 51, 55, 59, 63}
};
#endif
int
get_numa_id(int mytid)
{
#if INTEL_E5
    int ret = 0;

    for (int i = 0; i < 4; i++)
        for (int j = 0; j < 16; j++)
            if (numa[i][j] == mytid) {
                ret = i;
                break;
            }

    return ret;
#elif INTEL_XEON_GOLD_6226
    int ret = 0;

    for (int i = 0; i < 2; i++)
        for (int j = 0; j < 24; j++)
            if (numa[i][j] == mytid) {
                ret = i;
                break;
            }

    return ret;
#elif INTEL_XEON_E5_2697
    int ret = 0;
    for (int i = 0; i < 2; i++)
        for (int j = 0; j < 28; j++)
            if (numa[i][j] == mytid) {
                ret = i;
                break;
            }

    return ret;
#elif INTEL_XEON_E5_2690
    int ret = 0;
    for (int i = 0; i < 2; i++)
        for (int j = 0; j < 16; j++)
            if (numa[i][j] == mytid) {
                ret = i;
                break;
            }

    return ret;
#elif INTEL_XEON_GOLD_6230
    int ret = 0;
    for (int i = 0; i < 2; i++)
        for (int j = 0; j < 40; j++)
            if (numa[i][j] == mytid) {
                ret = i;
                break;
            }

    return ret;
#elif INTEL_XEON_PHI_7250
    return 0;
#else
    return 0;
#endif
}

int
get_num_numa_regions(void)
{
    /* TODO: FIXME automate it from the system config. */
#if INTEL_E5
    return 4;
#elif INTEL_XEON_GOLD_6226
    return 2;
#elif INTEL_XEON_E5_2690
    return 2;
#elif INTEL_XEON_E5_2697
    return 2;
#elif INTEL_XEON_GOLD_6230
    return 2;
#elif INTEL_XEON_PHI_7250
    return 1;
#else
    return 1;
#endif
}

int
get_numa_node_of_address(void * ptr)
{
    int numa_node = 0;
    get_mempolicy(&numa_node, NULL, 0, ptr, MPOL_F_NODE | MPOL_F_ADDR);
    return numa_node;
}
