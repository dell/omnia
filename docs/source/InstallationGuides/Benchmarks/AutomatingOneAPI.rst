Automate installation oneAPI on Intel processors for MPI jobs
------------------------------------------------------------------

This topic explains how to automatically update servers for MPI jobs. To manually install oneAPI, `click here. <OneAPI.html>`_

**Pre-requisites**

* ``provision.yml`` has been executed.
* An Omnia **slurm** cluster has been set up by ``omnia.yml`` running with at least 2 nodes: 1 manager and 1 compute.
* Verify that the target nodes are in the ``booted`` state. For more information, `click here <../InstallingProvisionTool/ViewingDB.html>`_.

**To run the playbook**::


    cd benchmarks
    ansible-playbook intel_benchmark.yml -i inventory


**To execute multi-node jobs**

* Make sure to have NFS shares on each node.
* Copy slurm script to NFS share and execute it from there.
* Load all the necessary modules using module load: ::

    module load mpi
    module load pmi/pmix-x86_64
    module load mkl

* If the commands/batch script are to be run over TCP instead of Infiniband ports, include the below line: ::

    export FI_PROVIDER=tcp


Job execution can now be initiated.

.. note:: Ensure ``runme_intel64_dynamic`` is downloaded before running this command.

::

    srun -N 2 /mnt/nfs_shares/appshare/mkl/2023.0.0/benchmarks/mp_linpack/runme_intel64_dynamic


For a batch job using the same parameters, the script would be: ::


    #!/bin/bash
    #SBATCH --job-name=testMPI
    #SBATCH --output=output.txt
    #SBATCH --partition=normal
    #SBATCH --nodelist=node00004.omnia.test,node00005.omnia.test

    pwd; hostname; date
    export FI_PROVIDER=tcp
    module load pmi/pmix-x86_64
    module use /opt/intel/oneapi/modulefiles
    module load mkl
    module load mpi

    srun  /mnt/appshare/benchmarks/mp_linpack/runme_intel64_dynamic
    date


