Network
=======

In your HPC cluster, connect the Mellanox InfiniBand switches using the Fat-Tree topology. In the fat-tree topology, switches in layer 1 are connected through the switches in the upper layer, i.e., layer 2. And, all the cluster nodes in the cluster, such as PowerEdge servers and PowerVault storage devices, are connected to switches in layer 1. With this topology in place, we ensure that a 1x1 communication path is established between the cluster nodes. For more information on the fat-tree topology, see `Designing an HPC cluster with Mellanox infiniband-solutions <https://community.mellanox.com/s/article/designing-an-hpc-cluster-with-mellanox-infiniband-solutions>`_.

.. note::

    * From Omnia 1.4, the Subnet Manager runs on the target Infiniband switches and not the control plane.

    * When ``ib_nic_subnet`` is provided in ``input/provision_config.yml``, the infiniband NIC on target nodes are assigned IPv4 addresses within the subnet without user intervention during the execution of ``provision.yml``.


Some of the network features Omnia offers are:

1. Mellanox OFED

2. Infiniband switch configuration

To install OFED drivers, enter all required parameters in ``input/network_config.yml``:


+------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Name                         | Description                                                                                                                                                                             |
+==============================+=========================================================================================================================================================================================+
| mlnx_ofed_offline_path       | Absolute path to local copy of .tgz file containing mlnx_ofed   package.  The package can be downloaded   from https://network.nvidia.com/products/infiniband-drivers/linux/mlnx_ofed/. |
|      [optional]              |                                                                                                                                                                                         |
|      ``string``              |                                                                                                                                                                                         |
+------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| mlnx_ofed_version            | Indicates the version of   mlnx_ofed to be downloaded. If ``mlnx_ofed_offline_path`` is not given,   declaring this variable is mandatory.                                              |
|      [optional]              |                                                                                                                                                                                         |
|      ``string``              | **Default value**: 5.7-1.0.2.0                                                                                                                                                          |
+------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| mlnx_ofed_add_kernel_support | Indicates whether the kernel   needs to be upgraded to be compatible with mlnx_ofed.                                                                                                    |
|      [required]              |                                                                                                                                                                                         |
|      ``boolean``             | **Choices**:                                                                                                                                                                            |
|                              |                                                                                                                                                                                         |
|                              |      * ``false`` <- Default                                                                                                                                                             |
|                              |      * ``true``                                                                                                                                                                         |
+------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

To run the script: ::

    cd network
    ansible-playbook network.yml

