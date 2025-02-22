#!/bin/bash
#SBATCH --job-name=santi.meteore.deepmod
#SBATCH -q batch
#SBATCH -N 1 # number of nodes
#SBATCH -n 8 # number of cores
#SBATCH --mem 300G # memory pool for all cores
#SBATCH -t 72:00:00 # time (D-HH:MM:SS)
#SBATCH -o log/%x.%j.out # STDOUT
#SBATCH -e log/%x.%j.err # STDERR

set -x

NanoCompareDir=/projects/li-lab/yang/workspace/nano-compare
pythonFile=${NanoCompareDir}/src/nanocompare/utils/saniti-ecoli/sanity_meteore_deepmod.py

PHTHONPATH=${NanoCompareDir}/src python ${pythonFile} $@
