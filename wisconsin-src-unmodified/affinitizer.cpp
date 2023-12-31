/*
    Copyright 2011, Spyros Blanas.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

#include "affinitizer.h"
#include "exceptions.h"

#define linux
#ifdef linux
#include <sched.h>
#include <sys/syscall.h>
#include <unistd.h>
#elif solaris
#endif

/**
 * Caller is affinitized to particular CPU.
 */
void Affinitizer::affinitize(int threadid)
{
	// If oversubscribing, let OS figure it out.
	//
	if (totalthreads > totalcpus) {
		return;
	}

	// The code below has been hard-coded to use one out of the two CPUs in
	// our two-socket, six-core Intel X5650 system. Change the function that
	// maps threadid to the cpu_set_t mask to reflect your system.
	//
	// throw AffinitizationException();

#ifdef linux
	// It seams that for a N-core machine, 0..N cores are first, followed by
	// N+1...2*N SMT cores. NUMA nodes seem to be interleaved, aka core 0 is on
	// NUMA 0, core 1 is on NUMA 1, core 2 on NUMA 0, etc.
	//
	int offset;
	const int numanodes = 2;
	const int corespernode = 8;

	// Start on NUMA 0, then SMT on NUMA 0, then NUMA 1, then SMT NUMA 1.
	//
	// offset = (threadid * numanodes + threadid / corespernode) % (numanodes * corespernode);

	// Use SMT after 4 threads
	int mapping[] = {0, 1, 2, 3, 16, 17, 18, 19};
	offset = mapping[threadid];

	// Affinitize this thread at CPU \a offset.
	//
	cpu_set_t mask;
	CPU_ZERO(&mask);

	CPU_SET(offset, &mask);
	int tid = syscall(SYS_gettid);

	if (sched_setaffinity(tid, sizeof(cpu_set_t), &mask) == -1) {
		throw AffinitizationException();
	}
#else
#warning Affinitization not implemented yet!
#endif
}
