Upgrading Omnia
================

The upgrade feature in v1.6 helps customers to upgrade their Omnia setup from v1.5.1 to v1.6. This includes upgrading the essential software requirements, configurations, and cluster software.

**Prerequisites**

    1. Ensure to choose a server outside your intended cluster to function as your control plane.

    2. The control plane must have internet connectivity, GitHub installed, and run a full version of the operating system.

    3. Clone the Omnia v1.6 github repository on to the control plane using the following command: ::

           git clone https://github.com/dell/omnia.git

    4. Once the cloning process is done, follow the steps listed below to invoke the upgrade process:

.. toctree::

    prepare_config
    prepare_upgrade
    upgrade