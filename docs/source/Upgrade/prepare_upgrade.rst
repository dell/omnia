Prepare Upgrade
================

This playbook performs the following tasks:

    * Run validations on the Omnia v1.6 input configuration
    * Cleanup v1.5.1 telemetry by preserving the persistent data
    * Cleanup v1.5.1 openLDAP packages on control plane
    * Cleanup v1.5.1 Kubernetes on cluster
    * Creates the v1.6 local repository based on the auto-generated ``software_config.json`` after running ``prepare_config.yml``.
    * Prepares the control plane which includes upgrading xcat, setting up omnia telemetry binaries for cluster, restoring the omniaDB backup to v1.6 format.

To use the playbook, execute the following command: ::

    ansible-playbook prepare_upgrade.yml -i<Omnia1.5.1 inventory>
