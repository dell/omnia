Updating kernels
=================

**Pre requisites**:

* Verify that the BaseOS repo version on the control plane matches the cluster kernel version for the cluster nodes. ::

    dnf repolist

* Verify that the cluster nodes are in the ``booted`` state. For more information, `click here <../InstallingProvisionTool/ViewingDB.html>`_.

**Download and install kernel updates to cluster nodes**

1. Download all required kernel RPM update files to the ``/install/post/otherpkgs/<Provision OS.Version>/x86_64/custom_software/Packages/`` folder.

For example: ::

    cd /install/post/otherpkgs/rhels8.6.0/x86_64/custom_software/Packages/
    dnf download kernel* --resolve -y

2. Once downloaded, make sure there are >=20~ rpm packages in the ``/install/post/otherpkgs/rhels8.6.0/x86_64/custom_software/Packages/`` directory.
3. Inside the ``/install/post/otherpkgs/<Provision OS.Version>/x86_64/custom_software`` folder, create a file named ``update.otherpkgs.pkglist`` with the contents: ::

    custom_software/kernel*

4. Go to ``utils/os_package_update`` and edit ``package_update_config.yml``. For more information on the input parameters, `click here <../../Roles/Utils/OSPackageUpdate.html>`_.
5. Run ``package_update.yml`` using : ``ansible-playbook package_update.yml``
6. After execution is completed, verify that ``kernel`` packages are on the nodes using: ``rpm -qa | grep kernel``