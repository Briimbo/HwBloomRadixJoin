#!/bin/bash
# script to rerun the experiments performed by Balkesen et al. on their code and the code provided in wisconsin-src by Blanas et al.

FIGURE_5=0
FIGURE_9=0
FIGURE_11=0
FIGURE_12=0
ALL=0
while [ $# -gt 0 ] 
do
  case "$1" in
    -h|--help)
      echo "  $(basename "$0") [-h] [-all] [-figure5] [-figure9] [-figure11] [-figure12] - reruns the experiments by Balkesen et al.

      to reproduce the data for figure 5, 9, 11, 12 which will be put in folders according to the specific arguments (figureN). 
      The filenames are of the format <ALGO>_<WORKLOAD>_<NTHREADS>.txt
      The data may be analyzed with the plot_basics.py script in ../measurements by running python3 plot_basics.py"
      exit
      ;;
    -figure5)
      shift
      FIGURE_5=1
      ;;
    -figure9)
      shift
      FIGURE_9=1
      ;;
    -figure11)
      shift
      FIGURE_11=1
      ;;
    -figure12)
      shift
      FIGURE_12=1
      ;;
    -all)
      shift
      ALL=1
      ;;
    *)
      echo "$1 is not a recognized flag!"
      exit 1
      ;;
  esac
done  

exit

EXPERIMENTS_DIR="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
DIR=`dirname $EXPERIMENTS_DIR`
SRC_DIR=$DIR/src
WISCONSIN_SRC_DIR=$DIR/wisconsin-src-unmodified
RES_DIR=$DIR/base_results
WORKLOAD_A="--r-seed=12345 \
            --r-size=16777216 \
            --s-seed=54321 \
            --s-size=268435456"

WORKLOAD_B="--r-seed=12345 \
            --r-size=128000000 \
            --s-seed=54321 \
            --s-size=128000000"

# backup cpu-mapping.txt
if [ -f "$SRC_DIR/cpu-mapping.txt" ] 
then
  CPU_MAPPING_EXISTS=true
  mv $SRC_DIR/cpu-mapping.txt $SRC_DIR/_____cpu-mapping.txt.bak
fi

CPU_MAPPING_NEHALEM_ON_SANDY_BRIDGE="16 0 1 2 3 16 17 18 19 4 5 6 7 8 9 10 11 12 13 14 15"

# ===============================
# Prepare wisconsin-src reruns for Fig. 5 or 12
# ===============================
if [[ 'ALL + FIGURE_5 + FIGURE_12' -gt 0 ]]
then
  printf "Preparing data and setup for wisconsin experiments ..."
  cd $SRC_DIR
  sed -i '1 i\#define PERSIST_RELATIONS 1' generator.c
  make clean > /dev/null 2>&1
  make > /dev/null 2>&1
  ./mchashjoins -n "8" $WORKLOAD_A > /dev/null 2>&1
  tail -n +2 generator.c > generator_tmp.c && mv generator_tmp.c generator.c
  make clean > /dev/null 2>&1
  make > /dev/null 2>&1
  sed -i 's/ /|/' R.tbl
  sed -i 's/ /|/' S.tbl
  tail -n +2 R.tbl > 016M_build.tbl
  tail -n +2 S.tbl > 256M_probe.tbl
  mv 016M_build.tbl $WISCONSIN_SRC_DIR/datagen
  mv 256M_probe.tbl $WISCONSIN_SRC_DIR/datagen

  cd $WISCONSIN_SRC_DIR
  make > /dev/null 2>&1
  export LD_LIBRARY_PATH=$PWD/dist/lib/:$LD_LIBRARY_PATH
  cd conf/gen
  ./gen.sh
  printf "\b\b\b\b. Done.\n"
fi

# ===============================
# Rerun experiments for Fig. 5
# ===============================
if [[ 'ALL + FIGURE_5' -gt 0 ]]
then
  echo "Experiments for Fig. 5"
  echo "Preparing execution"

  echo $CPU_MAPPING_NEHALEM_ON_SANDY_BRIDGE > $SRC_DIR/cpu-mapping.txt

  mkdir -p $RES_DIR/figure5

  cd $DIR
  ./configure --enable-key8B --enable-timing > /dev/null 2>&1
  make clean > /dev/null 2>&1
  make > /dev/null 2>&1

  printf "\n Running experiments for Fig. 5 ...\n"

  printf "Algo\t| A/B\t| Threads | Status\n"
  echo "--------|-------|---------|--------"

  for n_threads in {1..8}
  do    
    printf "NPO \t| A \t| %d \t  | ..." "$n_threads"
    cd $SRC_DIR
    ./mchashjoins -a NPO -n $n_threads $WORKLOAD_A > $RES_DIR/figure5/NPO_A_$n_threads.txt
    printf "\b\b\b\b done\n"
    
    printf "NO \t| A \t| %d \t  | ..." "$n_threads"
    cd $WISCONSIN_SRC_DIR
    ./multijoin conf/gen/$n_threads/032768_no.conf > $RES_DIR/figure5/NO_A_$n_threads.txt
    printf "\b\b\b\b done\n"
  done

  rm $SRC_DIR/cpu-mapping.txt
fi


# ===============================
# Rerun experiments for Fig. 9
# ===============================
if [[ 'ALL + FIGURE_9' -gt 0 ]]
then
  echo "Experiments for Fig. 9"
  echo "Preparing execution"

  echo $CPU_MAPPING_NEHALEM_ON_SANDY_BRIDGE > $SRC_DIR/cpu-mapping.txt

  mkdir -p $RES_DIR/figure9

  cd $DIR
  ./configure --enable-timing > /dev/null 2>&1
  make clean > /dev/null 2>&1
  make > /dev/null 2>&1

  printf "\n Running experiments for Fig. 9 ...\n"

  printf "Algo\t| A/B\t| radix_bits | Status\n"
  echo "--------|-------|------------|--------"

  cd $SRC_DIR

  initial_n_radix_bits=`cat prj_params.h | grep -oP '#define NUM_RADIX_BITS \K.*'`
  last_n_radix_bits=$initial_n_radix_bits

  for n_radix_bits in {12..17}
  do
    sed -i "s/#define NUM_RADIX_BITS ${last_n_radix_bits}/#define NUM_RADIX_BITS ${n_radix_bits}/" prj_params.h
    printf "PRO \t| B \t| %d \t     | ..." "$n_radix_bits"
    make clean > /dev/null 2>&1
    make > /dev/null 2>&1
    ./mchashjoins -a PRO -n 8 $WORKLOAD_B > $RES_DIR/figure9/PRO_B_$n_radix_bits.txt
    printf "\b\b\b\b done\n"
    last_n_radix_bits=$n_radix_bits
  done

  sed -i "s/#define NUM_RADIX_BITS ${last_n_radix_bits}/#define NUM_RADIX_BITS ${initial_n_radix_bits}/" prj_params.h
  rm $SRC_DIR/cpu-mapping.txt
fi


# ===============================
# Rerun experiments for Fig. 11
# ===============================
if [[ 'ALL + FIGURE_11' -gt 0 ]]
then
  echo "Experiments for Fig. 11"
  echo "Preparing execution"

  echo $CPU_MAPPING_NEHALEM_ON_SANDY_BRIDGE > $SRC_DIR/cpu-mapping.txt

  mkdir -p $RES_DIR/figure11

  cd $DIR
  ./configure --enable-timing > /dev/null 2>&1
  make clean > /dev/null 2>&1
  make > /dev/null 2>&1

  printf "\n Running experiments for Fig. 11 ...\n"

  printf "Algo\t| A/B\t| radix_bits | Status\n"
  echo "--------|-------|------------|--------"

  cd $SRC_DIR

  initial_n_radix_bits=`cat prj_params.h | grep -oP '#define NUM_RADIX_BITS \K.*'`
  last_n_radix_bits=$initial_n_radix_bits

  for n_radix_bits in {12..16}
  do
    sed -i "s/#define NUM_RADIX_BITS ${last_n_radix_bits}/#define NUM_RADIX_BITS ${n_radix_bits}/" prj_params.h
    printf "PRO \t| B \t| %d \t     | ..." "$n_radix_bits"
    make clean > /dev/null 2>&1
    make > /dev/null 2>&1
    ./mchashjoins -a PRO -n 8 $WORKLOAD_B > $RES_DIR}/figure11/PRO_B_$n_radix_bits.txt
    printf "\b\b\b\b done\n"
    
    # without SIMD
    printf "PRH \t| B \t| %d \t     | ..." "$n_radix_bits"
    ./mchashjoins -a PRH -n 8 $WORKLOAD_B > $RES_DIR/figure11/PRH_B_$n_radix_bits.txt
    printf "\b\b\b\b done\n"
    
    # with SIMD
    printf "PRHO \t| B \t| %d \t     | ..." "$n_radix_bits"
    ./mchashjoins -a PRHO -n 8 $WORKLOAD_B > $RES_DIR/figure11/PRHO_B_${n_radix_bits}.txt
    printf "\b\b\b\b done\n"
    
    last_n_radix_bits=$n_radix_bits
  done

  sed -i "s/#define NUM_RADIX_BITS ${last_n_radix_bits}/#define NUM_RADIX_BITS ${initial_n_radix_bits}/" prj_params.h
  rm $SRC_DIR/cpu-mapping.txt
fi


# ===============================
# Rerun experiments for Fig. 12
# ===============================

if [[ 'ALL + FIGURE_12' -gt 0 ]]
then
  echo "Experiments for Fig. 12"
  echo "Preparing execution"

  echo $CPU_MAPPING_NEHALEM_ON_SANDY_BRIDGE > $SRC_DIR/cpu-mapping.txt

  mkdir -p $RES_DIR/figure12

  cd $DIR
  ./configure --enable-key8B --enable-timing > /dev/null 2>&1
  make clean > /dev/null 2>&1
  make > /dev/null 2>&1

  printf "\n Running experiments for Fig. 12 ...\n"

  printf "Algo\t| A/B\t| Threads | Status\n"
  echo "--------|-------|---------|--------"


  for n_threads in {1..8}
  do    
    cd $SRC_DIR
    printf "PRO \t| A \t| %d \t  | ..." "$n_threads"
    ./mchashjoins -a PRO -n $n_threads $WORKLOAD_A > $RES_DIR/figure12/PRO_A_$n_threads.txt
    printf "\b\b\b\b done\n"

    printf "RADIX \t| A \t| %d \t  | ..." "$n_threads"
    cd $WISCONSIN_SRC_DIR
    ./multijoin conf/gen/$n_threads/032768_radix2.conf > $RES_DIR/figure12/RADIX_A_$n_threads.txt
    printf "\b\b\b\b done\n"
  done

  rm $SRC_DIR/cpu-mapping.txt
fi

# Restore cpu-mapping.txt
if [ $CPU_MAPPING_EXISTS ]
then
  mv $SRC_DIR/_____cpu-mapping.txt.bak $SRC_DIR/cpu-mapping.txt
else
  rm -f $SRC_DIR/cpu-mapping.txt
fi
