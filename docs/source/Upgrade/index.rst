Upgrade Omnia OIM
==============================

To upgrade the Omnia version 1.6.1 to version 1.7 on your OIM, you can use the ``upgrade_oim.yml`` playbook in Omnia 1.7. This ensures that your OIM is running the latest version and includes any new features and improvements that are available.

.. caution:: Do not reboot the OIM before initiating the upgrade process, as it leads to loss of telemetry data.

.. note::

    * Before initiating upgrade, ensure that the OIM has a stable internet connection to avoid intermittent issues caused by poor network connectivity.
    * After upgrading the Omnia OIM running on a `supported OS <../Overview/SupportMatrix/OperatingSystems/index.html>`_ (except RHEL/Rocky Linux 8.6 and 8.8), the ``input/software_config.json`` file remains in its default state. This enables users to install the default software versions on a new cluster.

**Tasks performed by the** ``upgrade_oim.yml`` **playbook**

The ``upgrade_oim.yml`` playbook performs the following tasks:

* Validates whether upgrade can be performed on the Omnia OIM.
* Takes backup of the Kubernetes etcd database, TimescaleDB, and MySQLDB at the backup location specified by the user.
* Regenerates the inventory files with hostname values.
* Imports input parameters from provided source code path of already installed Omnia version.
* Upgrades the software version for nerdctl and kubernetes on the OIM.
* Upgrades ``omnia_telemetry`` binaries on nodes where the telemetry service is running.
* Upgrades iDRAC telemetry services on the OIM.

**Pre-check before Upgrade**

If you have deployed a telemetry service in your Kubernetes cluster, it is important to ensure that the cluster is running properly before you initiate the upgrade process. As part of the upgrade pre-check, Omnia verifies if there are any issues with the cluster, such as non-running pods, LoadBalancer services without external IPs, or unbounded PVCs. If any of these issues are detected, you will need to address them before you can proceed with the upgrade.

**Steps to be performed for Upgrade**

To upgrade the Omnia OIM, do the following:

1. Clone the Omnia 1.7 source code to your OIM using the following command: ::

    git clone https://github.com/dell/omnia.git

2. Execute the ``prereq.sh`` script using the following command: ::

    cd omnia
    ./prereq.sh

3. Use any one of the following commands to activate the Omnia virtual environment, based on the operating system running on the OIM:

    * For RHEL or Rocky Linux 8.8, and Ubuntu 20.04 or 22.04, use: ::

        source /opt/omnia/omnia17_venv/bin/activate

    * On RHEL/Rocky Linux 8.6 or 8.7, use: ::

        source /opt/omnia/omnia161_venv/bin/activate

4. Update the ``omnia/upgrade/upgrade_config.yml`` file with the following details:

    +-----------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------+
    | ``installed_omnia_path``    | * This variable points to the currently installed Omnia 1.6.1 source code directory.                                                            |
    |      Required               | * **Example**: ``/root/omnia161/omnia``                                                                                                         |
    |                             | .. note:: Verify that the directory has not been altered since the last execution of ``discovery_provision.yml`` and ``omnia.yml`` playbooks.   |
    +-----------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------+
    | ``backup_location``         | * This variable points to the directory where the Omnia OIM backup is stored during the upgrade process.                                        |
    |    Optional                 | * User must create this directory before running ``upgrade_oim.yml`` playbook and provide the complete path of that directory.                  |
    |                             | * If the specified directory doesn't exist, backups will be taken at ``/opt/omnia/backup_before_upgrade``                                       |
    |                             | * **Example**: ``/opt/omnia/upgrade_backup``                                                                                                    |
    +-----------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------+

5. Finally, execute the ``upgrade_oim.yml`` playbook using the following command: ::

    cd upgrade
    ansible-playbook upgrade_oim.yml

.. caution::

    If ``upgrade_oim.yml`` execution fails, you can rollback to Kubernetes version 1.26.12 and restore the old backed-up data using the ``restore_oim.yml`` playbook. To restore, do the following:

        1. Activate the Omnia virtual environment using the ``source /opt/omnia/omnia161_venv/bin/activate`` command.

        2. Execute the ``restore_oim.yml`` playbook using the following command: ::

            cd upgrade
            ansible-playbook restore_oim.yml

**Post Upgrade**

Things to keep in mind after the OIM has been upgraded successfully:

* To use Omnia 1.7 features, ensure to execute all the playbooks from within the Omnia 1.7 virtual environment. To activate the 1.7 virtual environment, use the following command: ::

    source /opt/omnia/omnia17_venv/bin/activate

* After upgrading your Omnia OIM to version 1.7, the new cluster configuration features added in this version won’t work with any of your existing clusters. These new features will only be available when you create new clusters on RHEL/Rocky Linux 8.8 or Ubuntu 22.04 platforms, using Omnia 1.7 source code.
* The new cluster configuration features in Omnia 1.7 are not supported on RHEL/Rocky Linux 8.6 or 8.7. This means that even if you upgrade your Omnia OIM to version 1.7, these features won’t function on those platforms.
* Post-upgrade to Omnia 1.7, if you want to use old 1.6.1 software versions of Kubernetes (1.26.12), KServe (0.11.2), Kubeflow (1.8.0), and MPI operator (0.4.0), then perform the following steps:

    * Activate the Omnia 1.6.1 virtual environment using the following command: ::

        source /opt/omnia/omnia161_venv/bin/activate

    * Update the ``input/software_config.json`` file of Omnia 1.7 with the required software versions.

    * [Optional] Omnia recommends to take a backup of the ``input/software_config.json`` and all other configurations files in case you want to switch to Omnia 1.7 at a later point of time.

    * Copy the ``<software_name>.json`` files from the ``input/config/<cluster_os_type>/<cluster_os_version>`` folder in Omnia 1.6.1 and overwrite the existing files in the same directory of Omnia 1.7.

