#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include "perf_manager.h"
//#include <stdio.h>
#include <string.h>
#include <stdbool.h>

const char * counter_names[15] = {"cycles",
                                  "instructions",
                                  "cycle_activity.stalls_l1d_miss",
                                  "cycle_activity.stalls_l2_miss",
                                  "cycle_activity.stalls_l3_miss",
                                  "cycle_activity.stalls_mem_any",
                                  "dTLB-load-misses",
                                  "mem_inst_retired.stlb_miss_loads",
                                  "L1-dcache-load-misses",
                                  "l2_rqsts.miss",
                                  "LLC-load-misses",
                                  "node-loads",
                                  "node-load-misses",
                                  "mem_load_l3_miss_retired.local_dram",
                                  "mem_load_l3_miss_retired.remote_dram"};

void perf_group_init(struct PerfCounterGroup* group)
{
	group->count_members = 0;
}

void perf_group_add(struct PerfCounterGroup* group, char* name, int64_t type, int64_t event_id)
{
	const uint8_t index = group->count_members++;
	const bool is_leader = index == 0;
	
	memset(&group->event_attributes[index], 0, sizeof(struct perf_event_attr));
	group->event_attributes[index].type = type;
	group->event_attributes[index].size = sizeof(struct perf_event_attr);
	group->event_attributes[index].config = event_id;
	
	if (is_leader)
	{
		group->event_attributes[index].disabled = 1;
		group->event_attributes[index].read_format = PERF_FORMAT_TOTAL_TIME_ENABLED | PERF_FORMAT_TOTAL_TIME_RUNNING | PERF_FORMAT_GROUP | PERF_FORMAT_ID;
	}
	else
	{
		group->event_attributes[index].read_format = PERF_FORMAT_GROUP | PERF_FORMAT_ID;
	}
	
	group->names[index] = name;
	
	int32_t leader_file_descriptor = -1;
	if (is_leader == false)
	{
		leader_file_descriptor = group->file_descriptors[0];
	}
	
	group->file_descriptors[index] = syscall(__NR_perf_event_open, &group->event_attributes[index], 0, -1, leader_file_descriptor, 0);
	ioctl(group->file_descriptors[index], PERF_EVENT_IOC_ID, &group->ids[index]);
}

void perf_group_close(struct PerfCounterGroup* group)
{
	for (uint8_t id = 0; id < group->count_members; ++id)
	{
		close(group->file_descriptors[id]);
		group->file_descriptors[id] = -1;
	}
}

void perf_group_start(struct PerfCounterGroup* group)
{
	if (group->count_members > 0)
	{
		ioctl(group->file_descriptors[0], PERF_EVENT_IOC_RESET, 0);
		ioctl(group->file_descriptors[0], PERF_EVENT_IOC_ENABLE, 0);
        
		read(group->file_descriptors[0], &group->start_value, sizeof(struct PerfCounterReadFormat));
	}
}

void perf_group_stop(struct PerfCounterGroup* group)
{
	if (group->count_members > 0)
	{
		read(group->file_descriptors[0], &group->end_value, sizeof(struct PerfCounterReadFormat));
        
		ioctl(group->file_descriptors[0], PERF_EVENT_IOC_DISABLE, 0);
	}
}

double perf_group_get_value(struct PerfCounterGroup* group, uint8_t index)
{
	uint64_t id = group->ids[index];

	uint64_t start = 0;
	uint64_t end = 0;
	for (uint8_t i = 0; i < group->start_value.count_counters; ++i)
	{
		if (group->start_value.values[i].id == id)
		{
			start = group->start_value.values[i].value;
		}
	}
	
	for (uint8_t i = 0; i < group->end_value.count_counters; ++i)
	{
		if (group->end_value.values[i].id == id)
		{
			end = group->end_value.values[i].value;
		}
	}
	
	const double multiplexing_correction = ((double)(group->end_value.time_enabled - group->start_value.time_enabled)) /
                                         ((double)(group->end_value.time_running - group->start_value.time_running));
                                         
     return ((double)(end - start)) * multiplexing_correction;
}

void perf_counter_manager_init(struct PerfCounterManager* manager)
{
	/// Group: CYCLES, INSTRUCTIONS
	perf_group_init(&manager->counter[0]);
	perf_group_add(&manager->counter[0], "cycles", PERF_TYPE_HARDWARE, PERF_COUNT_HW_CPU_CYCLES);
	perf_group_add(&manager->counter[0], "instructions", PERF_TYPE_HARDWARE, PERF_COUNT_HW_INSTRUCTIONS);
	
	/// Group: CYCLE_ACTIVITY_STALLS_L1D_MISS, CYCLE_ACTIVITY_STALLS_L2_MISS, CYCLE_ACTIVITY_STALLS_L3_MISS, CYCLE_ACTIVITY_STALLS_MEM_ANY
	perf_group_init(&manager->counter[1]);
	perf_group_add(&manager->counter[1], "cycle_activity.stalls_l1d_miss", PERF_TYPE_RAW, 0xc530ca3);
	perf_group_add(&manager->counter[1], "cycle_activity.stalls_l2_miss", PERF_TYPE_RAW, 0x55305a3);
	perf_group_add(&manager->counter[1], "cycle_activity.stalls_l3_miss", PERF_TYPE_RAW, 0x65306a3);
	perf_group_add(&manager->counter[1], "cycle_activity.stalls_mem_any", PERF_TYPE_RAW, 0x145314a3);
	
	/// Group: DTLB_LOAD_MISSES, STLB_LOAD_MISSES
	perf_group_init(&manager->counter[2]);
	perf_group_add(&manager->counter[2], "dTLB-load-misses", PERF_TYPE_HW_CACHE, PERF_COUNT_HW_CACHE_DTLB | (PERF_COUNT_HW_CACHE_OP_READ << 8) | (PERF_COUNT_HW_CACHE_RESULT_MISS << 16));
	perf_group_add(&manager->counter[2], "mem_inst_retired.stlb_miss_loads", PERF_TYPE_RAW, 0x5311d0);
	
	/// Group: L1D_LOAD_MISSES, L2_RQST_MISS, LLC_LOAD_MISSES
	perf_group_init(&manager->counter[3]);
	perf_group_add(&manager->counter[3], "L1-dcache-load-misses", PERF_TYPE_HW_CACHE, PERF_COUNT_HW_CACHE_L1D | (PERF_COUNT_HW_CACHE_OP_READ << 8) | (PERF_COUNT_HW_CACHE_RESULT_MISS << 16));
	perf_group_add(&manager->counter[3], "l2_rqsts.miss", PERF_TYPE_RAW, 0x533f24);
	perf_group_add(&manager->counter[3], "LLC-load-misses", PERF_TYPE_HW_CACHE, PERF_COUNT_HW_CACHE_LL | (PERF_COUNT_HW_CACHE_OP_READ << 8) | (PERF_COUNT_HW_CACHE_RESULT_MISS << 16));
	
	/// Group: NODE_LOADS, NODE_LOAD_MISSES, MEM_LOAD_L3_MISS_RETIRED_LOCAL_DRAM, MEM_LOAD_L3_MISS_RETIRED_REMOTE_DRAM
	perf_group_init(&manager->counter[4]);
	perf_group_add(&manager->counter[4], "node-loads", PERF_TYPE_HW_CACHE, PERF_COUNT_HW_CACHE_NODE | (PERF_COUNT_HW_CACHE_OP_READ << 8) | (PERF_COUNT_HW_CACHE_RESULT_ACCESS << 16));
	perf_group_add(&manager->counter[4], "node-load-misses", PERF_TYPE_HW_CACHE, PERF_COUNT_HW_CACHE_NODE | (PERF_COUNT_HW_CACHE_OP_READ << 8) | (PERF_COUNT_HW_CACHE_RESULT_MISS << 16));
	perf_group_add(&manager->counter[4], "mem_load_l3_miss_retired.local_dram", PERF_TYPE_RAW, 0x5301d3);
	perf_group_add(&manager->counter[4], "mem_load_l3_miss_retired.remote_dram", PERF_TYPE_RAW, 0x5302d3);
}

void perf_counter_manager_close(struct PerfCounterManager* manager)
{
	for (int i = 0; i < 5; ++i)
	{
		perf_group_close(&manager->counter[i]);
	}
}

void perf_counter_manager_start(struct PerfCounterManager* manager)
{
	for (int i = 0; i < 5; ++i)
	{
		perf_group_start(&manager->counter[i]);
	}
}

void perf_counter_manager_stop(struct PerfCounterManager* manager)
{
	for (int i = 0; i < 5; ++i)
	{
		perf_group_stop(&manager->counter[i]);
	}
}

void perf_counter_manager_aggregate_values(struct PerfCounterManager* manager, double *values)
{
	/// Group: CYCLES, INSTRUCTIONS
	values[0] += perf_group_get_value(&manager->counter[0], 0);
	values[1] += perf_group_get_value(&manager->counter[0], 1);
	
	/// Group: CYCLE_ACTIVITY_STALLS_L1D_MISS, CYCLE_ACTIVITY_STALLS_L2_MISS, CYCLE_ACTIVITY_STALLS_L3_MISS, CYCLE_ACTIVITY_STALLS_MEM_ANY
	values[2] += perf_group_get_value(&manager->counter[1], 0);
	values[3] += perf_group_get_value(&manager->counter[1], 1);
	values[4] += perf_group_get_value(&manager->counter[1], 2);
	values[5] += perf_group_get_value(&manager->counter[1], 3);
	
	/// Group: DTLB_LOAD_MISSES, STLB_LOAD_MISSES
	values[6] += perf_group_get_value(&manager->counter[2], 0);
	values[7] += perf_group_get_value(&manager->counter[2], 1);
	
	/// Group: L1D_LOAD_MISSES, L2_RQST_MISS, LLC_LOAD_MISSES
	values[8] += perf_group_get_value(&manager->counter[3], 0);
	values[9] += perf_group_get_value(&manager->counter[3], 1);
	values[10] += perf_group_get_value(&manager->counter[3], 2);
	
	/// Group: NODE_LOADS, NODE_LOAD_MISSES, MEM_LOAD_L3_MISS_RETIRED_LOCAL_DRAM, MEM_LOAD_L3_MISS_RETIRED_REMOTE_DRAM
	values[11] += perf_group_get_value(&manager->counter[4], 0);
	values[12] += perf_group_get_value(&manager->counter[4], 1);
	values[13] += perf_group_get_value(&manager->counter[4], 2);
	values[14] += perf_group_get_value(&manager->counter[4], 3);
}
