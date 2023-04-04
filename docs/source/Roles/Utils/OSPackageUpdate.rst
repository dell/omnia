OS Package Update
++++++++++++++++++

To install multiple packages on target nodes in a bulk operation, the ``package_update.yml`` playbook can be leveraged.

**Prerequisites**

    * All target nodes should be running RHEL 8.4, RHEL 8.5 or RHEL 8.6.
    * Download the packages (RPMs) for the target nodes and place them in an empty folder:  ``/install/<custom folder>``.
    * Create a package list by creating the following text file (For packages that are not in RHEL repos, name the file ``update.otherpkgs.pkglist``. For OS packages, ``xxxx.pkglist``) and placing it with the RPMs: ::

        <package1>-<version1>
        <package2>-<version2>
        <package3>-<version3>


To customize the package update, enter the following parameters in ``utils/package_update_config.yml``:

+------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Parameter        | Details                                                                                                                                                                                   |
+==================+===========================================================================================================================================================================================+
| os_version       | Comma separated list of RHEL versions of target nodes in the cluster.                                                                                                                     |
|      ``string``  |                                                                                                                                                                                           |
|      Required    |                                                                                                                                                                                           |
+------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| package_dir      | Path   in which the package RPMs are stored.                                                                                                                                              |
|      ``string``  |                                                                                                                                                                                           |
|      Required    |                                                                                                                                                                                           |
+------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| package_list     | * Location path for the package list file                                                                                                                                                 |
|      ``string``  | * For ``other`` packagelist, file name should be -   (xxx.otherpkgs.pkglist)                                                                                                              |
|      Required    | * For ``os`` packagelist, file name should be - (xxx.pkglist)                                                                                                                             |
|                  | * All packages in this list will be installed/updated on remote nodes                                                                                                                     |
+------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| package_type     | Indicates whether the packages to be installed are ``os`` packages (ie   they are available in baseos or appstream) or ``other`` (ie they're not part   of os repos, appstream or baseos) |
|      ``string``  |                                                                                                                                                                                           |
|      Required    | Choices:                                                                                                                                                                                  |
|                  |                                                                                                                                                                                           |
|                  |      * ``os``                                                                                                                                                                             |
|                  |      * ``other``                                                                                                                                                                          |
+------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| nodelist         | Comma separated list of all target nodes in the cluster.                                                                                                                                  |
|      ``string``  |                                                                                                                                                                                           |
|      Required    |      **Default values**: ``all``                                                                                                                                                          |
+------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| reboot_required  | Indicates whether the remote nodes listed will be rebooted.                                                                                                                               |
|      ``boolean`` |                                                                                                                                                                                           |
|      Required    | Choices:                                                                                                                                                                                  |
|                  |                                                                                                                                                                                           |
|                  |      * ``true`` <- Default                                                                                                                                                                |
|                  |      * ``false``                                                                                                                                                                          |
+------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+


To run the playbook, run the following commands: ::

    cd utils
    ansible-playbook package_update.yml

