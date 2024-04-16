OS Package Update
++++++++++++++++++

To install multiple packages on target nodes in a bulk operation, the ``software_update.yml`` playbook can be leveraged.

**Prerequisites**

    * All target nodes should be running RHEL, Rocky, or Ubuntu OS.
    * Download the packages using ``local_repo.yml``. For more information, `click here. <../../LocalRepo/index.html>`_.


To customize the software update, enter the following parameters in ``utils/software_update/software_update_config.yml``:

+------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Parameter        | Details                                                                                                                                                                                      |
+==================+==============================================================================================================================================================================================+
| softwares_list   | * Mandatory, when package_list is not provided                                                                                                                                               |
|      ``string``  | * This variable contains the list of software group mentioned in ``software_config.json``.                                                                                                   |
|      Required    | * Example: ``softwares_list:
|                  |                  - custom                                                                                                                                                      |
|                  | * In the above case, user is required to create custom.json under ``input/config/<cluster_os_type>/<cluster_os_version>/custom.json``. For example: ``input/config/ubuntu/22.04/custom.json``|
|                  | * This json should contain the list of packages, either .deb (for Ubuntu) or .rpm (for RHEL/Rocky), which are to be installed on remote nodes.                                               |
+------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| package_list     | * Mandatory, when softwares_list is not provided                                                                                                                                             |
|      ``string``  | * This variable contains the list of packages to be installed on remote nodes.software                                                                                                       |
|      Required    | * Example: ``package_list: - linux-generic - wget`` ::                                                                                                                                         |
|                  |
|                  | * Kernel package name of Ubuntu is ``linux-generic``, whereas for RHEL, it's just ``kernel*``.
+------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| reboot_required  | Indicates whether the remote nodes listed will be rebooted.                                                                                                                                  |
|      ``boolean`` |                                                                                                                                                                                              |
|      Required    | Choices:                                                                                                                                                                                     |
|                  |                                                                                                                                                                                              |
|                  |      * ``true``                                                                                                                                                                              |
|                  |      * ``false`` <- Default                                                                                                                                                                  |
+------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

To run the playbook, run the following commands: ::

    cd utils/software_update
    ansible-playbook software_update.yml -i inventory

Inventory should contain the IP of the target nodes. For example, ::

    10.5.0.101
    10.5.0.102