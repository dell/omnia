Discovery Mechanisms
-----------------------

Depending on the value of ``discovery_mechanism`` in ``input/provision_config.yml``, potential target servers can be discovered one of three ways:

.. toctree::
    mappingfile
    snmp
    bmc

**Mapping File**

Manually collect PXE NIC information for target servers and manually define them to Omnia using a mapping file using the below format:

**pxe_mapping_file.csv**

::

    MAC,Hostname,IP

    xx:yy:zz:aa:bb:cc,server,10.5.0.101

    aa:bb:cc:dd:ee:ff,server2, 10.5.0.102


**Pros**

    - Easily customized if the user maintains a list of MAC addresses.

**Cons**

    - The user needs to be aware of the MAC/IP mapping required in the network.
    - Servers require a manual PXE boot if iDRAC IPs are not configured.

For more information regarding mapping files, `click here <mappingfile.html>`_




**SNMP**

Omnia can query known switches (by IP and community string) for information on target node MAC IDs.

**Pros**
    - The method can be applied to large clusters.
    - User intervention is minimal.
**Cons**
    - Switches should be SNMP enabled.
    - Servers require a manual PXE boot if iDRAC IPs are not configured.
    - PXE NIC ranges should contain IPs that are double the iDRACs present (as NIC and iDRAC MACs may need to be mapped).

For more information regarding SNMP, `click here <snmp.html>`_

**BMC**

Omnia can also discover nodes via their iDRAC using IPMI.


**Pros**

    - Discovery is automatic when iDRAC is DHCP enabled.
    - Provisioning of servers is automatic irrespective of whether DHCP is enabled.

**Cons**

    - For iDRACs that are not DHCP enabled (ie Static), users need to enable IPMI manually.


For more information regarding BMC, `click here <bmc.html>`_