BMC
---

For automatic provisioning of servers and discovery, the BMC method can be used.

**Prerequisites**

* Set the IP address of the OIM. The OIM NIC connected to remote servers (through the switch) should be configured with two IPs (BMC IP and admin IP) in a shared LOM or hybrid setup. In case of a dedicated setup, a single IP (admin IP) is required.
.. image:: ../../../../images/ControlPlaneNic.png

* To assign IPs on the BMC network while discovering servers using a BMC details, target servers should be in DHCP mode or switch details should be provided.

* BMC credentials should be the same across all servers and provided as input to Omnia in the parameters explained below.

* Target servers should be configured to boot in PXE mode with the appropriate NIC as the first boot device.

* If the ``discovery_ranges`` provided are outside the ``bmc_subnet``, ensure the target nodes can reach the OIM.

* IPMI over LAN needs to be enabled for the BMC. ::

    racadm set iDRAC.IPMILan.Enable 1
    racadm get iDRAC.IPMILan


.. caution:: If you are re-provisioning your cluster (that is, re-running the ``discovery_provision.yml`` playbook) after a `clean-up <../../../Maintenance/cleanup.html>`_, ensure to use a different ``static_range`` against ``bmc_network`` in ``input/project_default/network_spec.yml`` to avoid a conflict with newly assigned servers. Alternatively, disable any OS available in the ``Boot Option Enable/Disable`` section of your BIOS settings (**BIOS Settings > Boot Settings > UEFI Boot Settings**) on all target cluster nodes.

- All target servers should be reachable from the ``admin_network`` specified in ``input/project_default/network_spec.yml``.

* BMC network details should be provided in the ``input/project_default/network_spec.yml`` file.

* Few things to keep in mind while entering details in ``input/project_default/network_spec.yml``:

    * Ensure that the netmask bits for the BMC network and the admin network are the same.

    * The static and dynamic ranges for the BMC network accepts multiple comma-separated ranges.

    * The network gateways on both admin and BMC networks are optional.

.. note:: If the value of ``enable_switch_based`` is set to true, nodes will not be discovered via BMC irrespective of the contents in ``input/network_spec.yml``.

Next step:

* `Provisioning the cluster <../installprovisiontool.html>`_