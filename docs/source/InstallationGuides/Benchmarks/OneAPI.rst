Install oneAPI for MPI jobs on Intel processors
________________________________________________

This topic explains how to manually install oneAPI for MPI jobs. To install oneAPI automatically, `click here. <AutomatingOneAPI.html>`_

**Pre-requisites**

* An Omnia **slurm** cluster running with at least 2 nodes: 1 manager and 1 compute.
* Verify that the target nodes are in the ``booted`` state. For more information, `click here <../InstallingProvisionTool/ViewingDB.html>`_.


**Download and install Intel oneAPI base toolkit & Intel oneAPI HPC toolkit to control plane**

1. Create a DNF repository file in the ``/temp`` directory as a normal user. ::

        tee > /tmp/oneAPI.repo << EOF
        [oneAPI]
        name=IntelÂ® oneAPI repository
        baseurl=https://yum.repos.intel.com/oneapi
        enabled=1
        gpgcheck=1
        repo_gpgcheck=1
        gpgkey=https://yum.repos.intel.com/intel-gpg-keys/GPG-PUB-KEY-INTEL-SW-PRODUCTS.PUB
        EOF

2. Move the newly created ``oneAPI.repo`` file to the YUM configuration directory. ::

    sudo mv /tmp/oneAPI.repo /etc/yum.repos.d

3. Switch to the ``/install/post/otherpkgs/<Provision OS.Version>/x86_64/custom_software/Packages/`` folder and execute:

For example: ``cd /install/post/otherpkgs/rhels8.6.0/x86_64/custom_software/Packages/``. ::

    dnf download intel-basekit --resolve --alldeps -y
    dnf download intel-hpckit --resolve --alldeps -y

.. note:: Use ``alldeps -y`` to download **all** dependencies related to OneAPI.

4. Once downloaded, make sure there are >=270~ rpm packages in the ``/install/post/otherpkgs/rhels8.6.0/x86_64/custom_software/Packages/`` directory.
5. Inside the ``/install/post/otherpkgs/<Provision OS.Version>/x86_64/custom_software`` folder, create a file named ``update.otherpkgs.pkglist`` with the contents: ::

    custom_software/intel-basekit
    custom_software/intel-hpckit

6. Go to ``utils/os_package_update`` and edit ``package_update_config.yml``. For more information on the input parameters, `click here <../../Roles/Utils/OSPackageUpdate.html>`_.
7. Run ``package_update.yml`` using : ``ansible-playbook package_update.yml``
8. After execution is completed, verify that ``intelhpckit`` and ``basekit`` packages are on the nodes using: ``rpm -qa | grep intel``


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



