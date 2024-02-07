Installing the provision tool
=============================

This playbook achieves the following tasks:

    * Discovers potential cluster nodes

    * Installs Rocky or RHEL on the nodes

    * Assigns admin/infiniband IPs with optional DHCP routing

    * Creates access to offline repositories

    * Configures a docker registry to pull images from the internet and store them locally

    * Optionally installs OFED and CUDA

.. toctree::

    provisionprereqs
    DiscoveryMechanisms/index
    installprovisiontool
    ViewingDB
    provisionservers

