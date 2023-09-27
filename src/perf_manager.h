#ifndef MX_PERF_COUNTER_H
#define MX_PERF_COUNTER_H

#include <stdint.h>
#include <linux/perf_event.h>
#include <asm/unistd.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <sys/syscall.h>

#define PERF_COUNTER_PER_GROUP 4

extern const char * counter_names[15];

struct PerfCounterReadFormat
{
	uint64_t count_counters;
    uint64_t time_enabled;
    uint64_t time_running;
    
    struct {
    	uint64_t value;
    	uint64_t id;
    } values[PERF_COUNTER_PER_GROUP];
};

struct PerfCounterGroup
{
	uint8_t count_members;
    int32_t file_descriptors[PERF_COUNTER_PER_GROUP];
    uint64_t ids[PERF_COUNTER_PER_GROUP];
    char *names[PERF_COUNTER_PER_GROUP];
    struct perf_event_attr event_attributes[PERF_COUNTER_PER_GROUP];
    struct PerfCounterReadFormat start_value;
    struct PerfCounterReadFormat end_value;
};

struct PerfCounterManager
{
	struct PerfCounterGroup counter[5];
};

void perf_group_init(struct PerfCounterGroup* group);
void perf_group_add(struct PerfCounterGroup* group, char* name, int64_t type, int64_t event_id);
void perf_group_close(struct PerfCounterGroup* group);
void perf_group_start(struct PerfCounterGroup* group);
void perf_group_stop(struct PerfCounterGroup* group);

double perf_group_get_value(struct PerfCounterGroup* group, uint8_t index);

void perf_counter_manager_init(struct PerfCounterManager* manager);
void perf_counter_manager_close(struct PerfCounterManager* manager);
void perf_counter_manager_start(struct PerfCounterManager* manager);
void perf_counter_manager_stop(struct PerfCounterManager* manager);

void perf_counter_manager_aggregate_values(struct PerfCounterManager* manager, double* values);


#endif//MX_PERF_COUNTER_H