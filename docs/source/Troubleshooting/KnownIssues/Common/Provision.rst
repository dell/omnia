Provision
==========

⦾ **Why doesn't my newly discovered server list a MAC ID in the cluster.nodeinfo table?**

Due to internal MAC ID conflicts on the target nodes, the MAC address will be listed against the target node using this format ``MAC ADDRESS 1 | MAC ADDRESS 2! *NOIP*`` in the xCAT node object.

.. image:: ../../../images/MACConflict.png


⦾ **Why does the task Assign admin NIC IP fail during discovery_provision.yml with errors?**

.. image:: ../../../images/AdminNICErrors.png

**Potential Cause:** Omnia validates the admin NIC IP on the control plane. If the user has not assigned an admin NIC IP in case of dedicated network interface type, an error message is returned. There is a parsing logic that is being applied on the blank IP and hence, the error displays twice.

**Resolution**: Ensure a control plane IP is assigned to the admin NIC.


⦾ **Why are some target servers not reachable after PXE booting them?**

**Potential Causes**:

1. The server hardware does not allow for auto rebooting

2. The process of PXE booting the node has stalled.

**Resolution**:

1. Login to the iDRAC console to check if the server is stuck in boot errors (F1 prompt message). If true, clear the hardware error or disable POST (PowerOn Self Test).

2. Hard-reboot the server to bring up the server and verify that the boot process runs smoothly. (If it gets stuck again, disable PXE and try provisioning the server via iDRAC.)


⦾ **Why does PXE boot fail with tftp timeout or service timeout errors?**

**Potential Causes**:

* RAID is configured on the server.

* Two or more servers in the same network have xCAT services running.

* The target cluster node does not have a configured PXE device with an active NIC.

**Resolution**:

* Create a Non-RAID or virtual disk on the server.

* Check if other systems except for the control plane have ``xcatd`` running. If yes, then stop the xCAT service using the following commands: ``systemctl stop xcatd``.

* On the server, go to **BIOS Setup -> Network Settings -> PXE Device**. For each listed device (typically 4), configure an active NIC under ``PXE device settings``


