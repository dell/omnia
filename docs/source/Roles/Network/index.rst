Network
=======

In your HPC cluster, connect the Mellanox InfiniBand switches using the Fat-Tree topology. In the fat-tree topology, switches in layer 1 are connected through the switches in the upper layer, i.e., layer 2. And, all the compute nodes in the cluster, such as PowerEdge servers and PowerVault storage devices, are connected to switches in layer 1. With this topology in place, we ensure that a 1x1 communication path is established between the compute nodes. For more information on the fat-tree topology, see `Designing an HPC cluster with Mellanox infiniband-solutions <https://community.mellanox.com/s/article/designing-an-hpc-cluster-with-mellanox-infiniband-solutions>`_.

.. note:: From Omnia 1.4, the Subnet Manager runs on the target Infiniband switches and not the control plane.

Omnia uses the server-based Subnet Manager (SM). SM runs in a Kubernetes namespace on the control plane. To enable the SM, Omnia configures the required parameters in the ``opensm.conf`` file. Based on the requirement, the parameters can be edited.

Some of the network features Omnia offers are:

1. Mellanox OFED

2. Infiniband switch configuration


+------------------------------+--------------------------+-----------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Name                         | Default, accepted values | Required? | Purpose                                                                                                                                                                                 |
+==============================+==========================+===========+=========================================================================================================================================================================================+
| mlnx_ofed_offline_path       |                          | optional  | Absolute path to local copy of .tgz file containing mlnx_ofed   package.  The package can be downloaded   from https://network.nvidia.com/products/infiniband-drivers/linux/mlnx_ofed/. |
+------------------------------+--------------------------+-----------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| mlnx_ofed_version            | 5.7-1.0.2.0              | optional  | Indicates the version of mlnx_ofed to be downloaded. If   ``mlnx_ofed_offline_path`` is not given, declaring this variable is   mandatory.                                              |
+------------------------------+--------------------------+-----------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| mlnx_ofed_add_kernel_support | optional                 | required  | Indicates whether the kernel needs to be upgraded to be compatible with   mlnx_ofed.                                                                                                    |
+------------------------------+--------------------------+-----------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
