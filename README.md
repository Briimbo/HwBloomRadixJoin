# Hardware-Conscious Bloom Filters for Join Acceleration
This is the code accompanying the master thesis with the title

>Hardware-Conscious Bloom Filter for Join Acceleration

written by Benjamin Laumann and supervised by Roland Kühn.

The code builds upon the implementation by Balkesen et al., which in turn used code from Blanas et al. (wisconsin-src).
The original `README` can be found in this folder under `README_orig` and explains further details about running a single execution.
All data presented in the thesis can be produced and plotted within a few steps using this repository.
Data collection may take a couple of days - depending on the system.

## Quick Start
To experiment with the bloom filter implementation, run the following steps
```
$ autoreconf
$ ./configure
$ make
$ cd src
```

You can now find out about configurable (bloom filter + other) parameters or enable the bloom filter by running
```
$ ./mchashjoins -h
$ ./mchashjoins -r 128000000 -s 1024000000 -q 0.01 -b basic -m 1073741824 -k 1
```

## Directory Structure:
The repository contains the following directories:

```
├── base_results        :for reproduction of the original results (script + collected data)
├── base_results_gondor :data from replication of the results on Skylake 
├── doc                 :Doxyfile by Balkesen et al. for generating documentation (not up-to-date)
├── lib                 :additional libraries (provided by Balkesen et al.)
│   └── intel-pcm-1.7   :performance counters
├── measurements        :files to produce the paper data + actually collected data
│   ├── data            :non-graphical data
│   │   ├── md          :processed tabular data
│   │   └── pkl         :collected data
│   └── plots           :generated plots
├── src                 :source code
├── wisconsin-src       :source code by Blanas et al. modified by Balkesen et al. (not runnable...)
└── wisconsin-src-unmodified :original source code by Blanas et al. modified to enable reproduction
```

## Machine Codenames
The following codenames are used for different architecture and machines:

| Architecture (cf. thesis) | CPU | Codename |
|:--|:--|:--|
| Sandy Bridge | Xeon E5-2690 0 | isengard |
| Haswell | Xeon E5-26907 v3 | celebrimbor |
| Skylake | Xeon Gold 6226 | gondor |
| Knights Landing (A) | Xeon Phi 7250 | forostar |
| Knights Landing (B) | Xeon Phi 7250 | mittalmar |

## Requirements
Data collection was successfully performed on the following environments

| Codename | Ubuntu | gcc | autoconf | automake | python | pandas | tabulate |
|----------|--------|-----|----------|----------|--------|--------|----------|
| Isengard | 20.04 | 9.4.0 | 2.69 | 1.16.1 | 3.8 | 0.25.3 | 0.9.0 |
| Gondor | 20.04 | 9.4.0 | 2.69 | 1.16.1 | 3.8 | 1.3.4 | 0.9.0 |
| Celebrimbor | 22.04 | 11.3.0 | 2.71 | 1.16.5 | 3.10 | 2.0.1 | 0.9.0 |
| Forostar | 22.04 | 11.3.0 | 2.71 | 1.16.5 | 3.10 | 1.3.5 | 0.9.0 |
| Mittalmar | 22.04 | 11.3.0 | 2.71 | 1.16.5 | 3.10 | 1.3.5 | 0.9.0 |

Additionally, the following versions were used for analysis:
1. python 3.10
1. matplotlib 3.7.1
1. pandas 2.0.1
1. PGF plots only: TeX Live 2022 (valid TeX installation should be sufficient), you can also just generate pdf plots and use a suitable backend by modifying `plot_basics.py` and `analysis.py` in the `measurements` folder

For formatting, clang-format 14 was used.

Note that these requirements may not be hard requirements as other version can also work correctly. These are just the configurations used without further analysis.

## Reproduction
To reproduce the experiments, proceed as follows (assuming you are located in the top-level folder):

### Preparation 
1. Ensure the requirements are met
1. Ensure the correct configuration of `cpu_mapping.c`, `cpu-mapping.txt` and possibly other configurations as specified in `README_orig`
1. Add system dependent configurations to `measurements/config.py` if they are not present yet
1. `$ BASE=$(pwd)`
1. `$ autoreconf && ./configure &6 make clean && make`

### Regenerate the data:
Generation might take a couple of days! You do not need to run this as the raw data is already included in this repository. You can collect it yourself by running

`$ python3 measurements/run.py`

To regenerate the data for unit-testing the bloom filter, run

`$ ./src/unittests 2 817263 1024000000 128000000 1073741824 12 > measurements/data/bloom_filter_fpr.txt`

and modify the resulting file by removing all `%`, replacing all `+` with `|`, fill the empty cells on the left with the contents from the last line that does not contain measured values and remove all those lines without measured values. An example can be found by comparing the shipped `measurements/data/bloom_filter_fpr_orig.txt` and its modified version `measurements/data/bloom_filter_fpr.txt`

For reproducing the original plots by Balkesen et al., the data is also already present. You can regenerate the data by running

`$ ./base_results/rerun-experiments.sh -all`

### Run the analysis to get the figures and data for tables of the thesis:

If you do not want to collect the data yourself, you can use the original raw data of the thesis to produce the figure and tables.
Otherwise, if you collected the data yourself, copy the data from all platforms into `measurements/data/pkl` and rename them by appending the platform, e.g., 

`$ mv hash_functions.pkl hash_functions_gondor.pkl`

and ensure that each file `test_parameters.pkl` is renamed to its platform, e.g., `gondor.pkl`. Also, ensure that all platforms are included in the `platforms` list in `analysis.py`. Then run the plot and table generation with 

`$ python3 measurements/analysis.py`

The plots (Fig. 6.1 - 6.8) will be located in `measurements/plots`, the tables (Tab. 6.1, 6.3, 6.5, 6.7, 6.8) will be in `measurements/data/md` (with more rows and columns than presented in the thesis)

For plotting the reproduction of original plots by Balkesen et al. (Fig 5.1 - 5.4), the filter validation (Fig 5.5) and the theoretical relation between k and the FPR (Fig 2.3), run 

`$ python3 measurements/plot_basics.py `

## Execution on different machines
Execution on different machines requires prior configuration as explained above.
Make sure to modify

* `cpu_mapping.c`
* `cpu-mapping.txt`
* `config.py`
* `analysis.py` (list of platforms)

to your needs as these are central for correct runs.

