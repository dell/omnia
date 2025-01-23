Step 3: Discover and provision the cluster
===========================================

The ``discovery_provision.yml`` playbook achieves the following tasks:

1. Installation and configuration of the provision tool.
2. Discovery of potential cluster nodes.
3. Provisioning the minimal version of RHEL/Rocky Linux OS on the discovered cluster nodes.

.. caution:: If you have a proxy server set up for your OIM, you must configure the proxy environment variables on the OIM before running any Omnia playbooks. For more information, `click here <../Setup_CP_proxy.html>`_.

.. toctree::
    :maxdepth: 2

    provisionprereqs
    DiscoveryMechanisms/index
    provisionparams
    installprovisiontool
    ViewingDB
