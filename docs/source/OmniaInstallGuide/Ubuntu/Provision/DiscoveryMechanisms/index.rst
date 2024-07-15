Discovery Mechanisms
-----------------------

Depending on the values provided in ``input/provision_config.yml``, target nodes can be discovered in one of three ways:

.. toctree::
    mappingfile
    switch-based
    bmc


**switch_based**

Omnia can query known switches (by SNMPv3 username/password) for information on target node MAC IDs.

**Pros**

- The whole discovery process is totally automatic.

- Admin IP, BMC IP and Infiniband IP address configuration is automatic on the target nodes.

- Re-provisioning of servers will be automatic.

- PXE booting servers is supported via split ports on the switch.

**Cons**

- Users need to enable IPMI on target servers.
- Servers require a manual PXE boot after the first run of the provision tool.

For more information regarding switch-based discovery, `click here <switch-based.html>`_

**mapping**

Manually collect PXE NIC information for target servers and manually define them to Omnia using a mapping file using the below format:

**pxe_mapping_file.csv**


::

    SERVICE_TAG,HOSTNAME,ADMIN_MAC,ADMIN_IP,BMC_IP
    XXXXXXXX,n1,xx:yy:zz:aa:bb:cc,10.5.0.101,10.3.0.101
    XXXXXXXX,n2,aa:bb:cc:dd:ee:ff,10.5.0.102,10.3.0.102


**Pros**

    - Easily customized if the user maintains a list of MAC addresses.

**Cons**

    - The user needs to be aware of the MAC/IP mapping required in the network.
    - Servers require a manual PXE boot if iDRAC IPs are not configured.

For more information regarding mapping files, `click here <mappingfile.html>`_

**bmc**

Omnia can also discover nodes via their iDRAC using IPMI.


**Pros**

    - Discovery and provisioning of servers is automatic.
    - Admin, BMC and Infiniband IP address configuration is automatic on the control plane.
    - LOM architecture is supported (including cloud enclosures: C6420, C6520, C6620).
**Cons**

    - For iDRACs that are not DHCP enabled (ie Static), users need to enable IPMI manually.


For more information regarding BMC, `click here <bmc.html>`_



