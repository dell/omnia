Sample Files
=============

inventory file
-----------------

.. caution:: All the file contents mentioned below are case sensitive.

::

        #Batch Scheduler: Slurm

        [slurm_control_node]

        10.5.1.101

        [slurm_node]

        10.5.1.103

        10.5.1.104

        [login]

        10.5.1.105



        #General Cluster authentication server

        [auth_server]

        10.5.1.106

        #AI Scheduler: Kubernetes

        [kube_control_plane]

        10.5.1.101

        [etcd]

        10.5.1.101

        [kube_node]

        10.5.1.102

        10.5.1.103

        10.5.1.104

        10.5.1.105

        10.5.1.106

.. note::

            * For Slurm, all the applicable inventory groups are ``slurm_control_node``, ``slurm_node``, and ``login``.
            * For Kubernetes, all the applicable groups are ``kube_control_plane``, ``kube_node``, and ``etcd``.
            * The centralized authentication server inventory group, that is ``auth_server``, is common for both Slurm and Kubernetes.
            * For secure login node functionality, ensure to add the ``login`` group in the provided inventory file.

software_config.json for RHEL
-------------------------------------------

::

    {
        "cluster_os_type": "rhel",
        "cluster_os_version": "9.6",
        "iso_file_path": "",
        "repo_config": "always",
        "softwares": [
            {"name": "amdgpu", "version": "6.3.1"},
            {"name": "cuda", "version": "12.8.0"},
            {"name": "ofed", "version": "24.10-1.1.4.0"},
            {"name": "service_node" },
            {"name": "openldap"},
            {"name": "nfs"},
            {"name": "k8s", "version":"1.31.4"},
            {"name": "slurm"}
        ],
        "amdgpu": [
            {"name": "rocm", "version": "6.3.1" }
        ],
        "slurm": [
            {"name": "slurm_control_node"},
            {"name": "slurm_node"},
            {"name": "login"}
        ]
    }



inventory file for additional NIC and Kernel parameter configuration
-------------------------------------------------------------------------

.. note:: You can use either node IPs, service tags, or hostnames, or any combination of them in the inventory file below.

Choose fom any of the templates provided below:

::

    #---------Template1---------

    [cluster1]
    10.5.0.1
    10.5.0.2

    [cluster1:vars]
    Categories=category-1

    #---------Template2---------

    [cluster2]
    10.5.0.5 Categories=category-4
    10.5.0.6 Categories=category-5

    #---------Template3---------

    10.5.0.3 Categories=category-2
    10.5.0.4 Categories=category-3

inventory file to delete node from the cluster
-------------------------------------------------

::

    [nodes]
    10.5.0.33

pxe_mapping_file.csv
------------------------------------

::

    SERVICE_TAG,HOSTNAME,ADMIN_MAC,ADMIN_IP,BMC_IP
    XXXXXXX,n1,xx:yy:zz:aa:bb:cc,10.5.0.101,10.3.0.101
    XXXXXXX,n2,aa:bb:cc:dd:ee:ff,10.5.0.102,10.3.0.102


powervault_inventory
------------------
::

    10.3.0.105


NFS Server inventory file
-------------------------

::

    #General Cluster Storage
    #NFS node
    [nfs]
    #node10


Inventory for iDRAC telemetry
------------------------------

::

    [idrac]
    10.10.0.1

.. note:: Only iDRAC/BMC IPs should be provided.

