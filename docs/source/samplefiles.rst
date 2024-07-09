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

software_config.json for Ubuntu
---------------------------------

::

        {
            "cluster_os_type": "ubuntu",
            "cluster_os_version": "22.04",
            "repo_config": "partial",
            "softwares": [
                {"name": "amdgpu", "version": "6.0"},
                {"name": "cuda", "version": "12.3.2"},
                {"name": "bcm_roce", "version": "229.2.61.0"},
                {"name": "roce_plugin"},
                {"name": "ofed", "version": "24.01-0.3.3.1"},
                {"name": "openldap"},
                {"name": "secure_login_node"},
                {"name": "nfs"},
                {"name": "beegfs", "version": "7.4.2"},
                {"name": "k8s", "version":"1.26.12"},
                {"name": "roce_plugin"},
                {"name": "jupyter"},
                {"name": "kubeflow"},
                {"name": "kserve"},
                {"name": "pytorch"},
                {"name": "tensorflow"},
                {"name": "vllm"},
                {"name": "telemetry"},
                {"name": "ucx", "version": "1.15.0"},
                {"name": "openmpi", "version": "4.1.6"}
            ],

            "bcm_roce": [
                {"name": "bcm_roce_libraries", "version": "229.2.61.0"}
            ],
            "amdgpu": [
                {"name": "rocm", "version": "6.0" }
            ],
            "vllm": [
                {"name": "vllm_amd"},
                {"name": "vllm_nvidia"}
            ],
            "pytorch": [
                {"name": "pytorch_cpu"},
                {"name": "pytorch_amd"},
                {"name": "pytorch_nvidia"}
            ],
            "tensorflow": [
                {"name": "tensorflow_cpu"},
                {"name": "tensorflow_amd"},
                {"name": "tensorflow_nvidia"}
            ]
        }

software_config.json for RHEL/Rocky Linux
-------------------------------------------

.. note:: For Rocky Linux OS, the ``cluster_os_type`` in the below sample will be ``rocky``.

::

        {
            "cluster_os_type": "rhel",
            "cluster_os_version": "8.8",
            "repo_config": "partial",
            "softwares": [
                {"name": "amdgpu", "version": "6.0"},
                {"name": "cuda", "version": "12.3.2"},
                {"name": "ofed", "version": "24.01-0.3.3.1"},
                {"name": "freeipa"},
                {"name": "openldap"},
                {"name": "secure_login_node"},
                {"name": "nfs"},
                {"name": "beegfs", "version": "7.4.2"},
                {"name": "slurm"},
                {"name": "k8s", "version":"1.26.12"},
                {"name": "jupyter"},
                {"name": "kubeflow"},
                {"name": "kserve"},
                {"name": "pytorch"},
                {"name": "tensorflow"},
                {"name": "vllm"},
                {"name": "telemetry"},
                {"name": "intel_benchmarks", "version": "2024.1.0"},
                {"name": "amd_benchmarks"},
                {"name": "utils"},
                {"name": "ucx", "version": "1.15.0"},
                {"name": "openmpi", "version": "4.1.6"}
            ],

            "amdgpu": [
                {"name": "rocm", "version": "6.0" }
            ],
            "vllm": [
                {"name": "vllm_amd"},
                {"name": "vllm_nvidia"}
            ],
            "pytorch": [
                {"name": "pytorch_cpu"},
                {"name": "pytorch_amd"},
                {"name": "pytorch_nvidia"}
            ],
            "tensorflow": [
                {"name": "tensorflow_cpu"},
                {"name": "tensorflow_amd"},
                {"name": "tensorflow_nvidia"}
            ]

        }

inventory file for IP rule assignment
---------------------------------------

::

     all:
       hosts:
         node1:
           nic_info:
             - { nic_name: eno20195np0, gateway: 10.10.1.254, metric: 101 }
             - { nic_name: eno20295np0, gateway: 10.10.2.254, metric: 102 }
             - { nic_name: eno20095np0, gateway: 10.10.3.254, metric: 103 }
             - { nic_name: eno19995np0, gateway: 10.10.4.254, metric: 104 }
             - { nic_name: eno19595np0, gateway: 10.10.5.254, metric: 105 }
             - { nic_name: eno19695np0, gateway: 10.10.6.254, metric: 106 }
             - { nic_name: eno19795np0, gateway: 10.10.7.254, metric: 107 }
             - { nic_name: eno19895np0, gateway: 10.10.8.254, metric: 108 }
         node02:
           nic_info:
             - { nic_name: enp129s0f0np0, gateway: 10.11.1.254, metric: 101 }
             - { nic_name: enp33s0f0np0, gateway: 10.11.2.254, metric: 102 }

inventory file for additional NIC configuration
------------------------------------------------

::

    [node-group1]
    10.5.0.3

    [node-group1:vars]
    Categories=group-1

    [node-group2]
    10.5.0.4
    10.5.0.5

    [node-group2:vars]
    Categories=group-2

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


switch_inventory
------------------
::

    10.3.0.101
    10.3.0.102


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

