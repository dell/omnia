Prepare Upgrade
================

This is the second step of upgrade process and uses the ``prepare_upgrade.yml`` playbook. This playbook performs the following tasks:

    * Runs validations on the Omnia v1.6.1 input configurations.
    * Cleanup of the Omnia v1.5.1 telemetry configuration while preserving the persistent data.
    * Cleanup of the Omnia v1.5.1 OpenLDAP packages from the control plane.
    * Cleanup of the Omnia v1.5.1 Docker installation from the control plane.
    * Cleanup of the Omnia v1.5.1 Kubernetes setup from the cluster.
    * Creates the v1.6.1 local repository based on the ``software_config.json``, generated after running ``prepare_config.yml``.
    * Unmounts the NFS share directory, mentioned as ``omnia_usrhome_share`` in v1.5.1 ``omnia_config.yml``, from the cluster and then deletes it.
    * In case where ``enable_omnia_nfs`` is set to true in v1.5.1 ``omnia_config.yml`` and the head node acts as the NFS server, the upgrade process disables the NFS server running on the head node and removes the NFS share mentioned in ``omnia_usrhome_share`` from the head node. The NFS server will be set up on the control plane as per Omnia v1.6.1.
    * Prepares the control plane which includes upgrading xCAT, setting up Omnia telemetry binaries for cluster, restoring the OmniaDB backup to v1.6.1 format.

.. caution:: The NFS share directory mentioned in ``omnia_usrhome_share``, provided in v1.5.1 ``omnia_config.yml``, is unmounted from the cluster and deleted from the head node, along with all the user data while executing the ``prepare_upgrade.yml`` playbook. Hence, it is recommended that you take a backup of the Omnia NFS share before executing the ``prepare_upgrade.yml`` playbook.

To execute the ``prepare_upgrade.yml`` playbook, run the following command: ::

    cd omnia/upgrade
    ansible-playbook prepare_upgrade.yml -i <Omnia_1.5.1_inventory_file_path>
