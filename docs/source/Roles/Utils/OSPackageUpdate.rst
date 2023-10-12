OS Package Update
++++++++++++++++++

To install multiple packages on target nodes in a bulk operation, the ``package_update.yml`` playbook can be leveraged.

**Prerequisites**

    * All target nodes should be running RHEL or Rocky (Versions 8.4, 8.5 or 8.6).
    * Download the packages (RPMs) for the target nodes and place them in this folder:  ``/install/post/otherpkgs/<Provision OS.Version>/x86_64/custom_software/Packages``.

        .. note:: Do not use ISO files for updates or package installations.

    * Create a package list by creating the following text file (For packages that are not in RHEL repos, name the file ``update.otherpkgs.pkglist``. For OS packages, ``xxxx.pkglist``) and place in the default path. For example: ``/install/post/otherpkgs/<Provision OS.Version>/x86_64/custom_software/update.otherpkgs.pkglist``: ::

        custom_software/<package1>-<version1>
        custom_software/<package2>-<version2>
        custom_software/<package3>-<version3>


To customize the package update, enter the following parameters in ``utils/package_update_config.yml``:

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
| package_type     | * Indicates whether the packages to be installed are ``os`` packages (ie   they are available in baseos or appstream) or ``other`` (ie they're not part of os repos, appstream or baseos).|
|      ``string``  | * If the package is being downloaded to ``/install/post/otherpkgs/<Provision OS.Version>/x86_64/custom_software/Packages/``, use the value ``other``.                                     |
|      Required    | Choices:                                                                                                                                                                                  |
|                  |                                                                                                                                                                                           |
|                  |      * ``os``                                                                                                                                                                             |
|                  |      * ``other`` <- Default                                                                                                                                                               |
+------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| nodelist         | Comma separated list of all target nodes in the cluster.                                                                                                                                  |
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

    cd utils
    ansible-playbook package_update.yml

.. note:: At the end of the playbook, the package update status is displayed by target node. If the update status of any node is ``failed``, use the command log (``/var/log/xcat/commands.log``) to debug the issue. Alternatively, verify that the node is reachable post provisioning.