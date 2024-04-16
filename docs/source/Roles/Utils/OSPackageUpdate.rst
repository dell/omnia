OS Package Update
++++++++++++++++++

To install multiple packages on target nodes in a bulk operation, the ``software_update.yml`` playbook can be leveraged.

**Prerequisites**

    * All target nodes should be running RHEL, Rocky, or Ubuntu OS.
    * Download the packages using ``local_repo.yml``. For more information, `click here. <../../LocalRepo/index.html>`_.


To customize the software update, enter the following parameters in ``utils/software_update/software_update_config.yml``:

+------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Parameter        | Details                                                                                                                                                                                   |
+==================+===========================================================================================================================================================================================+
| os_type          | The operating system in use on the target cluster nodes.                                                                                                                                  |
|      ``string``  |                                                                                                                                                                                           |
|      Required    |      Choices:                                                                                                                                                                             |
|                  |                                                                                                                                                                                           |
|                  |      * ``rhel``    <- Default                                                                                                                                                             |
|                  |                                                                                                                                                                                           |
|                  |      * ``rocky``                                                                                                                                                                          |
+------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| os_version       | OS version of target nodes in the cluster.                                                                                                                                                |
|      ``string``  |                                                                                                                                                                                           |
|      Required    | **Default value**: 8.6                                                                                                                                                                    |
+------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| package_list     | * Location path for the package list file                                                                                                                                                 |
|      ``string``  | * For other packagelist, file name should be -   (xxx.otherpkgs.pkglist)                                                                                                                  |
|      Required    | * For os packagelist, file name should be - (xxx.pkglist)                                                                                                                                 |
|                  | * All packages in this list will be installed/updated on remote nodes                                                                                                                     |
|                  | **Default value**: ``"/install/post/otherpkgs/rhels8.6.0/x86_64/custom_software/update.otherpkgs.pkglist"``                                                                               |
+------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| package_type     | * Indicates whether the packages to be installed are ``os`` packages (they are available in baseos or appstream) or ``other`` (they're not part of os repos, appstream or baseos).        |
|      ``string``  | * If the package is being downloaded to ``/install/post/otherpkgs/<Provision OS.Version>/x86_64/custom_software/Packages/``, use the value ``other``.                                     |
|      Required    | Choices:                                                                                                                                                                                  |
|                  |                                                                                                                                                                                           |
|                  |      * ``os``                                                                                                                                                                             |
|                  |      * ``other`` <- Default                                                                                                                                                               |
+------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| nodelist         | comma-separated list of all target nodes in the cluster.                                                                                                                                  |
|      ``string``  |                                                                                                                                                                                           |
|      Required    |      **Default value**: ``all``                                                                                                                                                           |
+------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| reboot_required  | Indicates whether the remote nodes listed will be rebooted.                                                                                                                               |
|      ``boolean`` |                                                                                                                                                                                           |
|      Required    | Choices:                                                                                                                                                                                  |
|                  |                                                                                                                                                                                           |
|                  |      * ``true``                                                                                                                                                                           |
|                  |      * ``false`` <- Default                                                                                                                                                               |
+------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

To run the playbook, run the following commands: ::

    cd utils/software_update
    ansible-playbook software_update.yml -i inventory

Inventory should contain the IP of the target nodes. For example,

        10.5.0.101
        10.5.0.102