#!/bin/bash
#SBATCH --job-name=testONEAPI
#SBATCH --output=output.txt
#SBATCH --partition=normal
#SBATCH -N 2 --nodelist=springnode00003.spring.test,springnode00004.spring.test

pwd; hostname; date

# Exporting enviorment variables
export FI_PROVIDER=tcp
source /opt/intel/oneapi/setvars.sh

#Below command can be used to run job from NFS share
cd /home/omnia-share/mp_linpack
srun -N 2 --mpi=pmix -n 2 xhpl_intel64_dynamic

date
