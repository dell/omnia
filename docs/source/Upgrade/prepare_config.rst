Prepare Config
===============

This playbook uses the ``upgrade_config.yml`` to import the configuration parameters from Omnia v1.5.1 and generates the input configurations and inventory for Omnia v1.6.

The ``upgrade_config.yml`` requires the following details:

+-----------------------------+------------------------------------------------------------------------------------------+
| Parameter                   |     Description                                                                          |
+========================================================================================================================+
| **old_input_location**      |     * This variable points to the input directory of the old Omnia 1.5.1 installation    |
|                             |     * **Example:** ``/root/omnia15/input``                                               |
+-----------------------------+------------------------------------------------------------------------------------------+
| **backup_location**         |     * This variable points to the directory where OmniaDB backups should be stored.      |
|                             |     * This directory must be provided. This is a mandatory detail.                       |
|                             |     * **Example:** ``/root/omnia-backups``                                               |
+-----------------------------+------------------------------------------------------------------------------------------+

The playbook also sets v1.6 execution environment by updating the ansible and python version to match to v1.6. A backup of OmniaDB is taken in configured location.

To use the playbook, execute the following command: ::

    cd upgrade
    ansible-playbook prepare_config.yml -i<Omnia1.5.1 inventory>

Expected output of this playbook execution:

    * Auto-populated v1.6 config files in the ``<omnia 1.6_location>/omnia/input``.
    * Auto-generated inventory file in 1.6 format. This is available in the upgrade folder and will be used later during the execution of `upgrade.yml <upgrade.html>`_.

**Review or Update the auto-generated config files**

Post ``prepare_config.yml`` execution, you must review or update the auto-populated config files in ``<omnia1.6_location>/omnia/input`` as mentioned below.

    * Review the ``software_config`` and ensure that the scheduler type matches with v1.5.1. Additionally, confirm that telemetry is added, if ``omnia_telemetry_support`` was enabled in v1.5.1's ``telemetry_config.yml``.
    * Add ``rhel_os_url`` or ``rocky_os_url`` in ``local repo_config.yml`` based on the type of control plane OS.
    * Verify ``input/network_spec.yml`` for ``admin_network`` and ``bmc_network`` details.
    * If your Omnia v1.5.1 installation had slurm set up, ensure that the v1.6 ``omnia_config.yml`` has ``slurm_installation_type`` updated as "configless".
    * The new inventory format for v1.6 will list all 1.5 Omnia head nodes as ``kube_control_plane`` and/or ``slurm_control_node`` based on the ``scheduler_type``.
    * All compute nodes will be listed as ``kube_node`` or ``slurm_node`` based on ``scheduler_type``.
    * Ensure that the OmniaDB backup has been created in the location provided in ``upgrade_config.yml``