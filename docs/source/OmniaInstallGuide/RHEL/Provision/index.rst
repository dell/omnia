Step 3: Install the provision tool
======================================

The provision tool is installed using an Ansible playbook. This playbook achieves the following tasks:

1. Discovers potential cluster nodes.
2. Installs minimal version of RHEL OS on the discovered cluster nodes.

.. toctree::
    :maxdepth: 2

    provisionprereqs
    DiscoveryMechanisms/index
    provisionparams
    installprovisiontool
    ViewingDB
    AdditionalNIC
