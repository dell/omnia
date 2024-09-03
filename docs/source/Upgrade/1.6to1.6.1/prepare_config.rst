Prepare Config
===============

This is the first step of upgrade process and uses the ``prepare_config.yml`` playbook. This playbook performs the following tasks:

    * Imports the input configuration parameters from Omnia v1.6 and generates the input configurations for v1.6.1.

Before executing ``prepare_config.yml``, user needs to update ``upgrade_config.yml`` with the following details:

+-----------------------------+------------------------------------------------------------------------------------------+
| Parameter                   |     Description                                                                          |
+=============================+==========================================================================================+
| **old_input_location**      |     * This variable points to the input directory of the old Omnia 1.6 installation      |
|   (Required)                |     * **Example input location:** ``/root/omnia15/omnia/input``                          |
+-----------------------------+------------------------------------------------------------------------------------------+
| **backup_location**         |     * This variable points to the directory where OmniaDB backups should be stored.      |
|   (Required)                |     * This directory must exist prior to running ``prepare_config.yml``                  |
|                             |     * **Example:** ``/root/omnia-backups``                                               |
+-----------------------------+------------------------------------------------------------------------------------------+

.. note:: During the upgrade from version 1.6 to 1.6.1, Omnia does not require the creation of a backup file. This is because none of the details from the Omnia database are deleted during the upgrade process.

To execute the ``prepare_config.yml`` playbook, run the following command: ::

    cd omnia/upgrade
    ansible-playbook prepare_config.yml -i <Omnia_1.6_inventory_file_path>

Expected output of this playbook execution:

    * Auto-populated Omnia v1.6.1 configuration files in the ``<omnia_1.6.1_location>/omnia/input``.