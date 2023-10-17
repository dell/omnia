Installing pmix and updating slurm configuration for AMD processors
--------------------------------------------------------------------

This topic explains how to automatically update AMD servers for MPI jobs. To manually install pmix and update the slurm configuration, `click here. <OpenMPI_AOCC.html>`_

**Pre-requisites**

* ``provision.yml`` has been executed.
* An Omnia **slurm** cluster has been set up by ``omnia.yml`` running with at least 2 nodes: 1 manager and 1 compute.
* Verify that the target nodes are in the ``booted`` state. For more information, `click here <../InstallingProvisionTool/ViewingDB.html>`_.

**To run the playbook**::

    cd benchmarks
    ansible-playbook amd_benchmark.yml -i inventory

**To execute multi-node jobs**

* OpenMPI and aocc-compiler-*.tar should be installed and compiled with slurm on all cluster nodes or should be available on the NFS share.

.. note::
    * Omnia currently supports ``pmix version2``, ``pmix_v2``.

    * While compiling OpenMPI, include ``pmix``, ``slurm``, ``hwloc`` and, ``libevent`` as shown in the below sample command: ::

                ./configure --prefix=/home/omnia-share/openmpi-4.1.5 --enable-mpi1-compatibility --enable-orterun-prefix-by-default --with-slurm=/usr --with-pmix=/usr --with-libevent=/usr --with-hwloc=/usr --with-ucx CC=clang CXX=clang++ FC=flang   2>&1 | tee config.out



* For a job to run on multiple nodes (10.5.0.4 and 10.5.0.5) where OpenMPI is compiled and installed on the NFS share (``/home/omnia-share/openmpi/bin/mpirun``), the job can be initiated as below:

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


Alternatively, to use ``mpirun``, the script would be: ::

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

    /home/omnia-share/openmpi/bin/mpirun --map-by ppr:1:node -np 2 --display-map   --oversubscribe --mca orte_keep_fqdn_hostnames 1 ./xhpl



.. note:: The above scripts are samples that can be modified as required. Ensure that ``--mca orte_keep_fqdn_hostnames 1`` is included in the mpirun command in sbatch scripts.  Omnia maintains all hostnames in FQDN format. Failing to include ``--mca orte_keep_fqdn_hostnames 1`` may cause job initiation to fail.

