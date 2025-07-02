================================
Dynamic Kubernetes installation
================================

Apart from the default Kubernetes version present in the ``input/software_config.json`` (1.31.4) Omnia also lets you choose your own Kubernetes version.
Based on the version that you choose, Omnia will download and configure all Kubernetes related packages required for the cluster.

.. note:: Currently Omnia can only the Kubernetes versions compatible with the last 3 releases of Kubespray.
    
Compatibility Matrix
==========================

Check the table below for the minimum and maximum Kubernetes version supported for the last 3 Kubespray release:

    +-------------------+----------------------------+----------------------------+
    | Kubespray Version | Minimum Kubernetes version | Maximum Kubernetes version |
    +===================+============================+============================+
    | 2.28.0            | 1.30.0                     | 1.32.5                     |
    +-------------------+----------------------------+----------------------------+
    | 2.27.0            | 1.29.0                     | 1.31.4                     |
    +-------------------+----------------------------+----------------------------+
    | 2.26.0            | 1.28.0                     | 1.30.4                     |
    +-------------------+----------------------------+----------------------------+

Prerequisites
===============

* Ensure that a compatilable version of ``omnia_kubespray`` image is present based on the version list mentioned above. To know about all the supported versions of Kubernetes for a specific release of Kubespray, check out `Kubespray on github <https://github.com/kubernetes-sigs/kubespray>`_. 
* Ensure that ``discovery_provision.yml`` has been executed and nodes are provisioned with OS.

Input file
============

Update the ``k8s`` version to a supported version of your choice, in the ``input/software_config.json``. For example, update the version to ``1.32.5`` as shown below: ::

    "softwares": [

            {"name":"k8s", "version": "1.32.5"},
    ]

Playbook executions
=====================

1. After filling up the required input in ``input/software_config.json``, run the ``prepare_oim.yml`` playbook. This playbook sets up the Kubespray container required for the updated Kubernetes version. ::

    cd /omnia/prepare_oim
    ansible-playbook prepare_oim.yml

2. Execute ``local_repo.yml`` to download the artifacts required to set up the desired Kubernetes version: ::

    cd /omnia/local_repo
    ansible-playbook local_repo.yml

3. Finally, execute ``scheduler.yml`` or ``omnia.yml`` to deploy the Kubernetes cluster: 

    ::

        cd /omnia/scheduler
        ansible-playbook scheduler.yml -i <inventory_filepath>

    ::

        cd /omnia
        ansible-playbook omnia.yml -i <inventory_filepath>

