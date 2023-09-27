#!/bin/bash

THREADS="1 2 3 4 5 6 7 8"
EXPO="15"
PASSES="2"
ALGORTHMS="no radix"

for t in $THREADS; do
	mkdir -p $t
	for a in $ALGORTHMS; do
		for e in $EXPO; do
			m4  -DALGORITHM=$a	\
				-DBUCKETS=$((1<<$e))	\
				-DSKIPBITS=$((24-$e-1))	\
				-DPAGESIZE=$((1<<$((24-$e+4))))	\
				-DTHREADS=$t	\
				template.m4		> $t/`printf %06d $((1<<$e))`_${a}.conf
			for passes in $PASSES; do
				m4  -DALGORITHM=radix	\
					-DBUCKETS=$((1<<$e))	\
					-DSKIPBITS=$((24-$e-1))	\
					-DPAGESIZE=$((1<<$((24-$e+4))))	\
					-DTHREADS=$t	\
					-DNUMPASSES=$passes	\
					template.radix.m4	> $t/`printf %06d $((1<<$e))`_radix${passes}.conf
				m4  -DALGORITHM=radix	\
					-DBUCKETS=$((1<<$e))	\
					-DSKIPBITS=$((24-$e-1))	\
					-DPAGESIZE=$((1<<$((24-$e+4))))	\
					-DTHREADS=$t	\
					-DNUMPASSES=$passes	\
					template.radixsteal.m4	> $t/`printf %06d $((1<<$e))`_radix${passes}steal.conf
			done
		done
	done
done
