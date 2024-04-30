Building clusters
------------------

1. In the ``input/omnia_config.yml``, ``input/security_config.yml``, ``input/telemetry_config.yml`` and [optional] ``input/storage_config.yml`` files, provide the `required details <schedulerinputparams.html>`_.


2. Create an inventory file in the *omnia* folder. Check out the `sample inventory <../../samplefiles.html>`_ for more information. If a hostname is used to refer to the target nodes, ensure that the domain name is included in the entry. IP addresses are also accepted in the inventory file.

.. include:: ../../Appendices/hostnamereqs.rst

.. note::
     * Omnia creates a log file which is available at: ``/var/log/omnia.log``.
     * If only Slurm is being installed on the cluster, docker credentials are not required.


3. ``omnia.yml`` is a wrapper playbook comprising of:

    i. ``security.yml``: This playbook sets up centralized authentication (LDAP/FreeIPA) on the cluster. For more information, `click here. <Authentication.html>`_
    ii. ``storage.yml``: This playbook sets up storage tools like `BeeGFS <BeeGFS.html>`_ and `NFS <NFS.html>`_.
    iii. ``scheduler.yml``: This playbook sets up job schedulers (Slurm or Kubernetes) on the cluster.
    iv. ``telemetry.yml``: This playbook sets up `Omnia telemetry and/or iDRAC telemetry <../../Roles/Telemetry/index.html>`_. It also installs `Grafana <https://grafana.com/>`_ and `Loki <https://grafana.com/oss/loki/>`_ as Kubernetes pods.

To run ``omnia.yml``: ::

        ansible-playbook omnia.yml -i inventory


.. note::
    * For a Kubernetes cluster installation, ensure that the inventory includes an ``[etcd]`` entry. etcd is a consistent and highly-available key value store used as Kubernetes' backing store for all cluster data. For more information, `click here. <https://kubernetes.io/docs/tasks/administer-cluster/configure-upgrade-etcd/>`_
    * If you want to view or edit the ``omnia_config.yml`` file, run the following command:

                - ``ansible-vault view omnia_config.yml --vault-password-file .omnia_vault_key`` -- To view the file.

                - ``ansible-vault edit omnia_config.yml --vault-password-file .omnia_vault_key`` -- To edit the file.

    * Use the ansible-vault view or edit commands and not the ansible-vault decrypt or encrypt commands. If you have used the ansible-vault decrypt or encrypt commands, provide 644 permission to the parameter files.

**Slurm job based user access**

To ensure security while running jobs on the cluster, users can be assigned permissions to access cluster  nodes only while their jobs are running. To enable the feature: ::

    cd scheduler
    ansible-playbook job_based_user_access.yml -i inventory

.. note::

    * The inventory queried in the above command is to be created by the user prior to running ``omnia.yml`` as ``scheduler.yml`` is invoked by ``omnia.yml``

    * Only users added to the 'slurm' group can execute slurm jobs. To add users to the group, use the command: ``usermod -a -G slurm <username>``.

**Configuring UCX and OpenMPI on the cluster**

If a local repository for UCX and OpenMPI has been configured on the cluster, the following configurations take place when running ``omnia.yml`` or ``scheduler.yml``.

    * UCX will be compiled and installed on the NFS share (based on the ``client_share_path`` provided in the ``nfs_client_params`` in  ``input/storage_config.yml``).
    * If the cluster uses Slurm and UCX, OpenMPI is configured to compile with the UCX and Slurm on the NFS share (based on the ``client_share_path`` provided in the ``nfs_client_params`` in  ``input/storage_config.yml``).
    * All corresponding compiled UCX and OpenMPI files will be saved to the ``<client_share_path>/compile`` directory on the nfs share.
    * All corresponding UCX and OpenMPI executables will be saved to the ``<client_share_path>/benchmarks/`` directory on the nfs share.










