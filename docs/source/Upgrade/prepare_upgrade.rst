Prepare Upgrade
================

This is second step of upgrade process and uses the ``prepare_upgrade.yml`` playbook. This playbook performs the following tasks:

    * Runs validations on the Omnia v1.6 input configuration
    * Cleanup v1.5.1 telemetry by preserving the persistent data
    * Cleanup v1.5.1 OpenLDAP packages on control plane
    * Cleanup v1.5.1 Docker on the control plane
    * Cleanup v1.5.1 Kubernetes on cluster
    * Creates the v1.6 local repository based on the ``software_config.json``, generated after running ``prepare_config.yml``.
    * Disables the NFS server running on the head node and unmounts/deletes the NFS share directory, mentioned as ``omnia_usrhome_share`` in v1.5.1 ``omnia_config.yml``, from the cluster. This task is performed if ``enable_omnia_nfs`` is set to ``true`` in Omnia v1.5.1.
    * Prepares the control plane which includes upgrading xCAT, setting up Omnia telemetry binaries for cluster, restoring the OmniaDB backup to v1.6 format.

To execute the ``prepare_upgrade.yml`` playbook, run the following command: ::

    cd omnia/upgrade
    ansible-playbook prepare_upgrade.yml -i <Omnia_1.5.1_inventory_file_path>
