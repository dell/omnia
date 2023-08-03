Open MPI AOCC HPL benchmark for AMD processors
----------------------------------------------

**Prerequisites**

* Provision the cluster and install slurm on all cluster nodes.
* OpenMPI should be installed and compiled with slurm on all cluster nodes or should be available on the NFS share.


**To execute multi-node jobs**

1. Update the following parameters in ``/etc/slurm/slurm.conf``: ::

    SelectType=select/cons_tres
    SelectTypeParameters=CR_Core
    TaskPlugin=task/affinity,task/cgroup

2. Restart ``slurmd.service`` on all compute nodes. ::

    systemctl stop slurmd
    systemctl start slurmd

3. Once the service restarts on the compute nodes, restart ``slurmctld.service`` on the manager node. ::

        systemctl stop slurmctld.service
        systemctl start slurmctld.service

4. Job execution can now be initiated. Provide the host list using ``srun`` and ``sbatch``. For example:

For a job to run on multiple nodes (``omnianode00001.omnia.test``,``omnianode00006.omnia.test`` and,``omnianode00005.omnia.test``) and OpenMPI is compiled and installed on the NFS share (``/home/omnia-share/openmpi/bin/mpirun``), the job can be initiated as below: ::


    srun -N 3 --partition=mpiexectrial /home/omnia-share/openmpi/bin/mpirun -host omnianode00001.omnia.test,omnianode00006.omnia.test,omnianode00005.omnia.test ./amd-zen-hpl-2023_07_18/xhpl

For a batch job using the same parameters, the command would be: ::



    #!/bin/bash
    
    #SBATCH --job-name=test
    
    #SBATCH --output=test.log
    
    #SBATCH --partition=normal
    
    #SBATCH -N 3
    
    #SBATCH --time=10:00
    
    #SBATCH --ntasks=2
    
     
    
     
    
    source /home/omnia-share/setenv_AOCC.sh
    
    export PATH=$PATH:/home/omnia-share/openmpi/bin
    
    export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/home/omnia-share/openmpi/lib
    

     
    
    mpirun  -host omnianode00001.omnia.test,omnianode00005.omnia.test ./amd-zen-hpl-2023_07_18/xhpl
    
    srun sleep 30





