Upgrade
----------

The upgrade feature allows users to upgrade from Omnia 1.5.1 to Omnia 1.6.

To initiate upgrade, fill out the following parameters in ``omnia/upgrade/upgrade_config.yml``:
    old_input_location
    backup_location

+-------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Name                    | Description                                                                                                                                                 |
+=========================+=============================================================================================================================================================+
| old_input_location      | Points to location of previous Omnia 1.5.1 input directory.                                                                          |
|      ``string``         | E.g '/home/omnia_1.5.1/omnia/input'                                                                                                                                                            |
|      Required           |                                                                                                                                                             |
|                         |                                                                                                                                                             |
+-------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| backup_location         | Points to desired location for Postgres Database Backups. This directory must exist prior to running prepare_config.yml                                                             |
|      ``string``         |                                                                                                                                                             |
|      Required           |                                                                                                                                                             |
|                         |                                                                                                                                                             |
+-------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+

STEP - 1
--------

Once ``omnia/upgrade/upgrade_config.yml`` is filled in, run the following command from ``omnia/upgrade``: ::

    ansible-playbook prepare_config.yml -i <omnia_1.5.1_inventory_file_path>

This playbook uses the input config ``upgrade_config.yml`` to import the configuration parameters from Omnia 1.5.1 and generates the Omnia 1.6 input configurations and inventory.
The playbook also sets Omnia v1.6 execution environment by updating the ansible and python version to match the Omnia v1.6 requirements. 
A backup of Omnia Database is taken in the ``backup_location`` specified in ``upgrade_config.yml``

The above playbook performs the following:
* Auto-populates Omnia v1.6 config files in the <omnia_1.6_location>/omnia/input .
* Auto-generates inventory file in Omnia 1.6 format. This is available in the ``omnia/upgrade`` folder.

STEP - 2
--------
Before proceeding further, users have to review and update (if required) the auto-populated Omnia v1.6 config files present in the ``<omnia_1.6_location>/omnia/input`` .
* Review the ``software_config.json`` file
* Update the ``local_repo_config.yml`` file: Add ``rhel_os_url`` when Control Plane OS is RHEL
* Verify the ``network_spec.yml``: Verify the values populated for admin_network and bmc_network
* Verify ``omnia_config.yml``: If the Omnia 1.5.1 setup has slurm configured, it will be upgraded as ``configless`` slurm installation 

Check the new Inventory created:
* The new inventory format will have all Omnia 1.5.1 ``manager`` hosts populated as ``kube_control_plane`` and/or ``slurm_control_node`` based on the scheduler_type.
* All Omnia 1.5.1 ``compute`` nodes would be populated as ``kube_node`` and/or ``slurm_node`` based on the scheduler_type.

Verify Omnia Database backup taken:
Ensure the database backup is created at the ``backup_location`` specified in upgrade_config.yml

Once everything is verified, run the following command from ``omnia/upgrade``: ::

    ansible-playbook prepare_upgrade.yml -i <omnia_1.5.1_inventory_file_path>

The above playbook performs the following:
* Run validations on the Omnia 1.6 input configuration files
* Cleanup Omnia v1.5.1 Telemetry by preserving the persistent data
* Cleanup Omnia v1.5.1 OpenLDAP packages on the Control Plane
* Cleanup Omnia v1.5.1 Kubernetes on the cluster
* Configures the Omnia v1.6 ``local_repo`` based on entries populated in ``software_config.json`` present in ``<omnia_1.6_location>/omnia/input``
* Prepares the Control Plane: This includes upgrading xcat, setting up Omnia telemetry binaries for cluster and restoring the Omnia DB backup to Omnia v1.6 format

STEP - 3
--------
This playbook upgrades the Omnia v1.5.1 cluster to Omnia v1.6. Run the following command from ``omnia/upgrade``: ::

    ansible-playbook upgrade.yml -i <omnia_1.6_auto_generated_inventory>

This playbook upgrades the control plane and cluster to Omnia 1.6
