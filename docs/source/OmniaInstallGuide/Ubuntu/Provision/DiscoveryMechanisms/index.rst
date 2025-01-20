Discovery Mechanisms
=====================

Depending on the values provided in ``input/provision_config.yml``, target nodes can be discovered in one of three ways:

.. toctree::
    :hidden:

    switch-based
    mappingfile
    bmc


switch_based
------------

Omnia can query known switches (by SNMPv3 username/password) for information on target node MAC IDs.

+---------------------------------------------------------+------------------------------------------------------+
| Pros                                                    | Cons                                                 |
+=========================================================+======================================================+
| The entire discovery process is totally automatic.      | Users need to enable IPMI on target servers.         |
+---------------------------------------------------------+-----------------------------------+------------------+
| Admin IP, BMC IP and Infiniband IP address configuration| Servers require a manual PXE boot after the first run|
| is automatic on the target nodes.                       | of the provision tool.                               |
+---------------------------------------------------------+------------------------------------------------------+
| Re-provisioning of servers will be automatic.           |                                                      |
+---------------------------------------------------------+------------------------------------------------------+
| PXE booting servers is supported via split ports on the |                                                      |
| switch.                                                 |                                                      |
+---------------------------------------------------------+------------------------------------------------------+

For more information regarding switch-based discovery, `click here <switch-based.html>`_

mapping
--------

Manually collect PXE NIC information for target servers and manually define them to Omnia using a mapping file using the below format:

**pxe_mapping_file.csv**
::

    SERVICE_TAG,HOSTNAME,ADMIN_MAC,ADMIN_IP,BMC_IP
    XXXXXXXX,n1,xx:yy:zz:aa:bb:cc,10.5.0.101,10.3.0.101
    XXXXXXXX,n2,aa:bb:cc:dd:ee:ff,10.5.0.102,10.3.0.102

+---------------------------------------------------------+------------------------------------------------------+
| Pros                                                    | Cons                                                 |
+=========================================================+======================================================+
| Easily customizable if the user maintains a list of     | The user needs to be aware of the MAC/IP mapping     |
| MAC addresses.                                          | required in the network.                             |
+---------------------------------------------------------+-----------------------------------+------------------+
|                                                         | Servers require a manual PXE boot if iDRAC IPs are   |
|                                                         | not configured.                                      |
+---------------------------------------------------------+------------------------------------------------------+

For more information regarding mapping files, `click here <mappingfile.html>`_

bmc
----

Omnia can also discover nodes via their iDRAC using IPMI.

+---------------------------------------------------------+------------------------------------------------------+
| Pros                                                    | Cons                                                 |
+=========================================================+======================================================+
| Discovery and provisioning of servers is automatic.     | For iDRACs that are not DHCP enabled (i.e., Static), |
|                                                         | users need to enable IPMI manually.                  |
+---------------------------------------------------------+-----------------------------------+------------------+
| Admin, BMC and Infiniband IP address configuration is   | Servers require a manual PXE boot after the first run|
| automatic on the OIM.                                   | of the provision tool.                               |
+---------------------------------------------------------+------------------------------------------------------+
| LOM architecture is supported                           |                                                      |
| (including cloud enclosures: C6420, C6520, C6620).      |                                                      |
+---------------------------------------------------------+------------------------------------------------------+

For more information regarding BMC, `click here <bmc.html>`_



