Open MPI AOCC HPL benchmark for AMD processors
----------------------------------------------

**Prerequisites**

1. Provision the cluster and install slurm on all cluster nodes.
2. Dependent packages have to be installed on the cluster nodes using the following steps:

    i. Download the dependent packages on the control plane:

        a. Create a package list::

            cd /install/post/otherpkgs/<os_version>/x86_64/custom_software/
            cat openmpi.pkglist

        b. Enter the following contents into ``openmpi.pkglist``: ::

                custom_software/pmix-devel
                custom_software/libevent-devel

        c. Download the packages: ::

            cd packages
            dnf download pmix-devel --resolve --alldeps
            dnf download libevent-devel --resolve --alldeps

    ii. Push the packages to the cluster nodes:

        a. Update the ``package_list`` variable in the ``os_package_update/os_package_update.conf`` file and save it. ::

                package_list: "/install/post/otherpkgs/<os_version>/x86_64/custom_software/openmpi.pkglist"

        b. Update the cluster nodes by running the ``package_update.yml`` playbook* ::

            ansible-playbook package_update.yml


3. OpenMPI and aocc-compiler-*.tar should be installed and compiled with slurm on all cluster nodes or should be available on the NFS share.

.. note::
    * Omnia currently supports ``pmix version2``, ``pmix_v2``.
    * While compiling OpenMPI, include ``pmix``, ``slurm``, ``hwloc`` and, ``libevent`` as shown in the below sample command: ::

            ./configure --prefix=/home/omnia-share/openmpi-4.1.5 --enable-mpi1-compatibility --enable-orterun-prefix-by-default --with-slurm=/usr --with-pmix=/usr --with-libevent=/usr --with-hwloc=/usr --with-ucx CC=clang CXX=clang++ FC=flang   2>&1 | tee config.out

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

4. Job execution can now be initiated. To initiate a job use the following sample commands.

For a job to run on multiple nodes (10.5.0.4 and 10.5.0.5) where OpenMPI is compiled and installed on the NFS share (``/home/omnia-share/openmpi/bin/mpirun``), the job can be initiated as below:
.. note:: Ensure ``amd-zen-hpl-2023_07_18`` is downloaded before running this command.

::

    srun -N 2 --mpi=pmix_v2 -n 2 ./amd-zen-hpl-2023_07_18/xhpl


For a batch job using the same parameters, the script would be: ::


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

    srun --mpi=pmix_v2 ./amd-zen-hpl-2023_07_18/xhpl


.. note:: If mpirun is used to initiate jobs, a host list is required as illustrated: ``mpirun -np 2 -host 10.5.0.4,10.5.0.5 ./amd-zen-hpl-2023_07_18/xhpl``


