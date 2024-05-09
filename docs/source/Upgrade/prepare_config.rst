Prepare Config
===============

This playbook imports the configuration parameters from Omnia v1.5.1 and generates the input configurations and inventory for Omnia v1.6.

Before executing ``prepare_config.yml``, you need to update ``upgrade_config.yml`` with the following details:

+-----------------------------+------------------------------------------------------------------------------------------+
| Parameter                   |     Description                                                                          |
+=============================+==========================================================================================+
| **old_input_location**      |     * This variable points to the input directory of the old Omnia 1.5.1 installation    |
|   (Required)                |     * **Example input location:** ``/root/omnia15/omnia/input``                          |
+-----------------------------+------------------------------------------------------------------------------------------+
| **backup_location**         |     * This variable points to the directory where OmniaDB backups should be stored.      |
|   (Required)                |     * This directory must exist prior to running ``prepare_config.yml``                  |
|                             |     * **Example:** ``/root/omnia-backups``                                               |
+-----------------------------+------------------------------------------------------------------------------------------+

The playbook also sets Omnia v1.6 execution environment by updating the ansible and python version to match to v1.6 requirements. A backup of OmniaDB is taken at the backup location specified in ``upgrade_config.yml``.

To use the playbook, execute the following command: ::

    cd upgrade
    ansible-playbook prepare_config.yml -i <Omnia_1.5.1_inventory_file_path>

Expected output of this playbook execution:

    * Auto-populated Omnia v1.6 config files in the ``<omnia_1.6_location>/omnia/input``.
    * Auto-generated inventory file in Omnia v1.6 format. This is available in the ``<omnia_1.6_location>/omnia/upgrade`` folder and will be used later during the execution of `upgrade.yml <upgrade.html>`_.

**Review or Update the auto-generated config files**

Post ``prepare_config.yml`` execution, you must review or update the auto-populated config files in ``<omnia1.6_location>/omnia/input`` as mentioned below.

    * Review the ``software_config.json`` which contains a list of all softwares identified for the cluster. For more information, click `here. <../InstallationGuides/LocalRepo/index.html>`_
        * Ensure that the scheduler type for Omnia v1.6 matches with v1.5.1.
        * Confirm that telemetry is added, if ``omnia_telemetry_support`` was enabled in Omnia v1.5.1's ``telemetry_config.yml``.
    * Add ``rhel_os_url`` in ``local repo_config.yml`` when the cluster OS type is RHEL.
    * Verify ``input/network_spec.yml`` for ``admin_network`` and ``bmc_network`` details.
    * If your Omnia v1.5.1 installation had slurm set up, ensure that the v1.6 ``omnia_config.yml`` has ``slurm_installation_type`` updated as "configless".
    * The new inventory format for Omnia v1.6 lists all Omnia v1.5 manager nodes as ``kube_control_plane`` and/or ``slurm_control_node`` based on the ``scheduler_type``.
    * All compute nodes will be listed as ``kube_node`` or ``slurm_node`` based on ``scheduler_type``.
    * Verify ``nfs_client_params`` details in ``input/storage_config.yml`` file, as mentioned below:
        * Omnia v1.6 upgrade configures the NFS server on the control plane. Verify that the ``server_ip`` corresponds to the IP address of the control plane.
        * Depending on the ``scheduler_type``, that is, Slurm or Kubernetes, either ``k8s_share`` or ``slurm_share`` will be set to ``true``.
    * Ensure that the OmniaDB backup has been created in the ``backup_location`` provided in ``upgrade_config.yml``.