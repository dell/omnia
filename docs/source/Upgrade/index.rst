Upgrade Omnia control plane
==============================

To upgrade the Omnia version version 1.6.1 to version 1.7 on your control plane, you can use the ``upgrade_cp.yml`` playbook in Omnia 1.7. This ensures that your control plane is running the latest version and includes any new features and improvements that are available.

.. caution:: Omnia does not allow users to perform downgrade operations, which means that once they have upgraded, they cannot revert back to a previous version of Omnia.

**Tasks performed by the playbook**

The ``upgrade_cp.yml`` playbook performs the following tasks:

* Validates whether upgrade can be performed on the Omnia control plane.
* Takes backup of Kubernetes etcd, Omnia database, and telemetry pods in provided location.
* Regenerates the inventory files with hostname values.
* Imports input parameters from provided source code path of already installed Omnia version.
* Upgrades the software version for nerdctl and kubernetes on the control plane.
* Upgrades ``omnia_telemetry`` binaries on nodes where the telemetry service is running.
* Upgrades iDRAC telemetry services on the control plane.

**Pre-check before Upgrade**

If you have deployed a telemetry service in your Kubernetes cluster, it is important to ensure that the cluster is running properly before you initiate the upgrade process. As part of the upgrade precheck, Omnia verifies if there are any issues with the cluster, such as non-running pods, LoadBalancer services without external IPs, or unbounded PVCs. If any of these issues are detected, you will need to address them before you can proceed with the upgrade.

**Steps to be performed for Upgrade**

To upgrade the Omnia control plane, do the following:

1. Clone the Omnia 1.7 source code to your control plane using the following command: ::

    git clone https://github.com/dell/omnia.git

2. Execute the ``prereq.sh`` script using the following command: ::

    cd omnia
    ./prereq.sh

3. Use any one of the following commands to activate the Omnia virtual environment, based on the operating system running on the control plane:

    * For RHEL or Rocky Linux 8.8, and Ubuntu 20.04 or 22.04, use: ::

        source /opt/omnia/omnia17_venv/bin/activate

    * On RHEL/Rocky Linux 8.6 or 8.7, use: ::

        source /opt/omnia/omnia161_venv/bin/activate

4. Update the ``input/upgrade_config.yml`` file with the following details:

    +-----------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------+
    | ``installed_omnia_path``    | * This variable points to the the path or location of the directory where the Omnia 1.6.1 source code is currently installed.                   |
    |      Required               | * **Example**: ``/root/omnia161/omnia``                                                                                                         |
    |                             | .. note:: Verify that the directory has not been altered since the last execution of ``discovery_provision.yml`` and ``omnia.yml`` playbooks.   |
    +-----------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------+
    | ``backup_location``         | * This variable points to the directory where OmniaDB backups should be stored during the upgrade process.                                      |
    |    Optional                 | * This is an user-created directory and this must be created prior to running ``upgrade_cp.yml`` playbook.                                      |
    |                             | * If this directory is not created or provided by the user, Omnia stores the OmniaDB backup files at ``/opt/omnia/backup_before_upgrade``       |
    |                             | * **Example**: ``/root/omnia-backups``                                                                                                          |
    +-----------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------+

5. Finally, execute the ``upgrade_cp.yml`` playbook using the following command: ::

    cd upgrade
    ansible-playbook upgrade_cp.yml

.. note::

    * After upgrading your Omnia control plane to version 1.7, you will not be able to use the new features for cluster configuration that are available in version 1.7 on your existing clusters. These new features will only be available on fresh installations of Omnia 1.7.
    * After upgrading your Omnia control plane running on RHEL/Rocky Linux 8.6/8.7, new features of Omnia 1.7 for cluster configuration are not supported. This means that you will not be able to use the new features and improvements that are available in version 1.7 for configuring your existing clusters.
    * After the upgrade, you need to activate the virtual environment using the ``source /opt/omnia/omnia161_venv/bin activate`` command prior to installing the below software versions:

        - Kubernetes 1.26.12
        - KServe 0.11.2
        - Kubeflow 1.8.0
        - MPI operator 0.4.0

.. caution::

    If ``upgrade_cp.yml`` execution fails, you can restore your control plane to its older state using the ``restore_cp.yml`` playbook. To restore, do the following:

        1. Activate the Omnia virtual environment using the ``source /opt/omnia/omnia161_venv/bin/activate`` command.

        2. Execute the ``restore_cp.yml`` playbook using the following command: ::

            cd upgrade
            ansible-playbook restore_cp.yml