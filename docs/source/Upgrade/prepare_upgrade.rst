Prepare Upgrade
================

This is the second step of upgrade process and uses the ``prepare_upgrade.yml`` playbook. This playbook performs the following tasks:

    * Runs validations on the Omnia v1.6 input configuration
    * Cleanup v1.5.1 telemetry by preserving the persistent data
    * Cleanup v1.5.1 OpenLDAP packages on control plane
    * Cleanup v1.5.1 Docker on the control plane
    * Cleanup v1.5.1 Kubernetes on cluster
    * Creates the v1.6 local repository based on the ``software_config.json``, generated after running ``prepare_config.yml``.
    * Unmounts the NFS share directory, mentioned as ``omnia_usrhome_share`` in v1.5.1 ``omnia_config.yml``, from the cluster and then deletes it.
    * In case where ``enable_omnia_nfs`` is set to true in v1.5.1 ``omnia_config.yml`` and the head node acts as the NFS server, the upgrade process disables the NFS server running on the head node and removes the NFS share mentioned in ``omnia_usrhome_share`` from the head node. The NFS server will be set up on the control plane as per Omnia v1.6.
    * Prepares the control plane which includes upgrading xCAT, setting up Omnia telemetry binaries for cluster, restoring the OmniaDB backup to v1.6 format.

To execute the ``prepare_upgrade.yml`` playbook, run the following command: ::

    cd omnia/upgrade
    ansible-playbook prepare_upgrade.yml -i <Omnia_1.5.1_inventory_file_path>
