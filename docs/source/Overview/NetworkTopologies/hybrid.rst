Network Topology: Hybrid setup
=============================

For an environment containing both LOM and BMC ports, the provision tool needs to be run twice to correctly manage all servers in the network.

.. image:: ../../images/Hybrid_NT.png

In a **Hybrid Setup**, the control plane and special nodes such as the head and login node are connected to the public network, while the iDRAC and the compute nodes use a shared LOM network.

* **Public Network (Blue line)**: This indicates that the control plane, head node, and login node is connected to the external public network.

* **Cluster Network (Green line)**: This indicates the admin network utilized by Omnia to provision the cluster nodes.

* **InfiniBand (IB) Network (Yellow line)**: The network used by the applications on the cluster nodes to communicate among each other.

**Recommended discovery mechanism**

* `mapping <../../InstallationGuides/InstallingProvisionTool/DiscoveryMechanisms/mappingfile.html>`_
* `bmc <../../InstallationGuides/InstallingProvisionTool/DiscoveryMechanisms/bmc.html>`_