#!/bin/sh
# Script to prepare and run the measurements for evaluation
# Requires access to the git repository as well as preconditions mentioned in the README.md

BASE_DIR=~/final_tests
rm -rf $BASE_DIR
mkdir $BASE_DIR
cd $BASE_DIR
git clone ssh://git@git.cs.tu-dortmund.de:2222/benjamin.laumann/master-thesis.git
cd master-thesis
autoreconf
cd measurements
python3 -m pip install pandas tabulate matplotlib
echo "Running tests, check file $BASE_DIR/run.log for detailed status..."
python3 run.py > $BASE_DIR/run.log
echo "Finished running tests"
