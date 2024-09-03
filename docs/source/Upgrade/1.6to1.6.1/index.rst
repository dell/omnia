Upgrade Omnia v1.6 to v1.6.1
==============================

The upgrade feature in v1.6.1 helps customers to upgrade their Omnia setup from v1.6 to v1.6.1.

.. note:: Omnia v1.6.1 addresses the issue of the unavailable dependent package 'libssl1.1_1.1.1f-1ubuntu2.22_amd64' required by Omnia 1.6 on Ubuntu 22.04 OS. For more information, see the `release notes <../../Overview/releasenotes.html#id1>`_.

**Prerequisites**

    1. The control plane must have internet connectivity and run a full version of the operating system.

    2. If Git is not installed on the control plane, install Git using the following command: ::

           dnf install git -y

    3. Clone the Omnia v1.6.1 repository from GitHub and place it in a directory on the control plane. This directory must be different from the one containing the Omnia v1.6 repository. Execute the following command to perform the cloning operation: ::

           git clone https://github.com/dell/omnia.git

Once the cloning process is done, follow the steps listed below to invoke the upgrade process:

.. toctree::

    prepare_config
    prepare_upgrade
    upgrade

