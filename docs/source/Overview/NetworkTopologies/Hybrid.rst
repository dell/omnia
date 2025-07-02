Network Topology: Hybrid Setup
=================================

.. note:: The following diagram is for representational purposes only.

.. image:: ../../images/Hybrid_NT.png

In a **Hybrid Setup**, the OIM and special nodes such as the head and login node are connected to the public network, while the iDRAC and the compute nodes use a shared LOM network.

* **Public Network (Blue line)**: This indicates the external public network which is connected to the internet. NIC2 of the OIM, Head node, and Login node [optional] is connected to the public network. Along with this, BMC NIC of the Head node is connected.

* **Admin Network and BMC network (Green line)**: This indicates the admin network and the BMC network utilized by Omnia to provision the cluster nodes and to control the cluster nodes using out-of-band management. NIC1 of all the nodes are connected to the private switch.

* **IB / Additional Ethernet Network (Yellow line)**: This indicates the Infiniband (IB) or the additional ethernet network used by applications on the cluster nodes to communicate among each other, using Mellanox or high-speed ethernet switch. OIM connectivity is optional for this switch.

.. note:: Omnia supports classless IP addressing, which allows the Admin network, BMC network, Public network, and the Additional network to be assigned different subnets. However, the Admin and BMC networks must be on the same subnet (represented by the ``netmask_bits`` parameter in the ``input/network_spec.yml`` file).

**Recommended discovery mechanism**

* `mapping <../../OmniaInstallGuide/RHEL_new/Provision/DiscoveryMechanisms/mappingfile.html>`_
* `bmc <../../OmniaInstallGuide/RHEL_new/Provision/DiscoveryMechanisms/bmc.html>`_