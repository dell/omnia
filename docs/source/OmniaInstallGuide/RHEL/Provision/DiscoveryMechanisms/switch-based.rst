switch_based
-------------

**Pre requisites**

* Set the value of ``enable_switch_based`` to true in ``input/provision_config.yml``. Additionally, ensure that the variable ``switch_based_details`` in ``input/provision_config.yml`` is populated with the IP address and port details of the ToR switch.

* Switch port range where all BMC NICs are connected should be provided.

* BMC credentials should be the same across all servers and provided as input to Omnia. All BMC network details should be provided in ``input/network_spec.yml``.

* SNMP v3 should be enabled on the switch and the credentials should be provided in ``input/provision_config_credentials.yml``.

* Non-admin user credentials for the switch need to be provided.

.. note::
    * To create an SNMPv3 user on S series switches (running  OS10), use the following commands:

        - To create SNMP view: ``snmp-server view test_view internet included``
        - To create SNMP group: ``snmp-server group testgroup 3 auth read test_view``
        - To create SNMP users: ``snmp-server user authuser1 testgroup 3 auth sha authpasswd1``
    * To verify the changes made, use the following commands:

        - To view the SNMP views: ``show snmp view``
        - To view the SNMP groups: ``show snmp group``
        - To view the SNMP users: ``show snmp user``
    * To save this configuration for later use, run: ``copy running-configuration startup-configuration``
    * For more information on SNMP on S series switch `click here <https://www.dell.com/support/manuals/en-cr/dell-emc-os-9/s3048-on-9.14.2.6-cli-pub/snmp-server-user?guid=guid-dbed1721-656a-4ad4-821c-589dbd371bf9&lang=en-us>`_
    * For more information on SNMP on N series switch `click here <https://www.dell.com/support/kbdoc/en-us/000133707/how-to-configure-snmpv3-on-dell-emc-networking-n-series-switches>`_



* IPMI over LAN needs to be enabled for the OIM. ::

    racadm set iDRAC.IPMILan.Enable 1
    racadm get iDRAC.IPMILan

* Target servers should be configured to boot in PXE mode with appropriate NIC as the first boot device.

* Set the IP address of the OIM. The OIM NIC connected to remote servers (through the switch) should be configured with two IPs (BMC IP and admin IP) in a shared LOM or hybrid set up. In the case dedicated network topology, a single IP (admin IP) is required.
.. image:: ../../../../images/ControlPlaneNic.png

.. caution::
    * Do not use daisy chain ports or the port used to connect to the OIM in ``switch_based_details`` in ``input/provision_config.yml``. This can cause IP conflicts on servers attached to potential target ports.
    * Omnia does not validate SNMP switch credentials, if the provision tool is run with incorrect credentials, use the clean-up script and re-run the provision tool with the correct credentials.
    * If you are re-provisioning your cluster (that is, re-running the ``discovery_provision.yml`` playbook) after a `clean-up <../../../Maintenance/cleanup.html>`_, ensure to use a different ``static_range`` against ``bmc_network`` in ``input/network_spec.yml`` to avoid a conflict with newly assigned servers. Alternatively, disable any OS available in the ``Boot Option Enable/Disable`` section of your BIOS settings (**BIOS Settings > Boot Settings > UEFI Boot Settings**) on all target nodes.


.. note::
    * If any of the target nodes have a pre-provisioned BMC IP, ensure that these IPs are not part of the ``static_range`` specified in ``input/network_spec.yml`` under the ``bmc_network`` to avoid any bmc IP conflicts.
    * In case of a duplicate node object, duplicate BMC nodes will be deleted automatically by the **duplicate_node_cleanup** service that runs every 30 minutes. When nodes are discovered via mapping and switch details, the nodes discovered via switch details will not be deleted. Delete the node manually `using the delete node playbook. <../../../Maintenance/deletenode.html>`_

* [Optional] To clear the configuration on Omnia provisioned switches and ports, `click here <../../../../Utils/portcleanup.html>`_.

Next step:

* `Provisioning the cluster <../installprovisiontool.html>`_