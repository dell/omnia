Automate installation oneAPI on Intel processors for MPI jobs
------------------------------------------------------------------

This topic explains how to automatically update servers for MPI jobs.

**Pre-requisites**

* A local repository has been set up by listing ``{"name": "intel_benchmarks", "version": "2024.1.0"},`` in ``input/software_config.json`` and running ``local_repo.yml``. For more information, `click here. <../CreateLocalRepo/index.html>`_
* ``discovery_provision.yml`` playbook has been executed.
* Verify that the target nodes are in the ``booted`` state. For more information, `click here <../Provision/ViewingDB.html>`_.
* The cluster has been set up with Slurm. For more information, `click here <../OmniaCluster/BuildingCluster/install_slurm.html>`_.
* An Omnia **slurm** cluster has been set up by ``omnia.yml`` with at least 2 nodes: 1 ``slurm_control_node`` and 1 ``slurm_node``.

**Sample inventory**
::
    [slurm_control_node]

    10.5.1.101

    [slurm_node]

    10.5.1.103

**To run the playbook**::


    cd benchmarks
    ansible-playbook intel_benchmark.yml -i inventory


**To execute multi-node jobs**

* Ensure to have NFS share on each node.
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


