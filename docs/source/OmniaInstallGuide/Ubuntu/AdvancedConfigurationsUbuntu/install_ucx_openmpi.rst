Configuring UCX and OpenMPI on the cluster
============================================

**Prerequisites**

* Ensure that ``ucx`` and ``openmpi`` entry is present in the ``softwares`` list in ``software_config.json``, as mentioned below: ::

    "softwares": [
                    {"name": "ucx", "version": "1.15.0"},
                    {"name": "openmpi", "version": "4.1.6"}
                 ]

.. note:: For clusters running on Ubuntu 24.04 OS, the versions for UCX and OpenMPI will be ``1.17.0`` and ``5.0.4`` respectively.

* Ensure to run ``local_repo.yml`` with the ``ucx`` and ``openmpi`` entry present in ``software_config.json``, to download all required UCX and OpenMPI packages.

* To install any benchmarking software like UCX or OpenMPI, ensure that ``k8s_share`` is set to ``true`` in `storage_config.yml <../OmniaCluster/schedulerinputparams.html#storage-config-yml>`_, for one of the entries in ``nfs_client_params``. If both are set to true, a higher precedence is given to ``slurm_share``.

**Inventory details**

* For UCX and OpenMPI, all the applicable inventory groups are ``slurm_control_node`` and ``kube_control_plane``.

* The inventory file must contain exactly 1 ``slurm_control_node`` or/and 1 ``kube_control_plane``.

**To install UCX and OpenMPI**

* UCX will be compiled and installed on the NFS share (based on the ``client_share_path`` provided in the ``nfs_client_params`` in  ``input/storage_config.yml``).

* If the cluster uses Slurm and UCX, OpenMPI is configured to compile with the UCX and Slurm on the NFS share (based on the ``client_share_path`` provided in the ``nfs_client_params`` in  ``input/storage_config.yml``).

Run either of the following commands:

    1. ::

            ansible-playbook omnia.yml -i inventory

    2. ::

            ansible-playbook scheduler.yml -i inventory

.. note::

            * All corresponding compiled UCX and OpenMPI files will be saved to the ``<client_share_path>/compile`` directory on the nfs share.
            * All corresponding UCX and OpenMPI executables will be saved to the ``<client_share_path>/benchmarks/`` directory on the nfs share.
            * The default OpenMPI version for Omnia is 4.1.6. If you change the version in the ``software.json`` file, make sure to update it in the ``openmpi.json`` file in the ``input/config`` directory as well.
            * To add new nodes to an existing cluster, click `here <../../Maintenance/addnode.html>`_.