Switch-Based
-------------


**Pre requisites**

* IP address for ToR switch needs to be provided.

* Switch port range where all BMC NICs are connected should be provided.

* SNMP v3 should be enabled on the switch.

* Non-admin user credentials for the switch need to be provided.

* IPMI over LAN needs to be enabled for the BMC.

* BMC NICs should have a static IP assigned or be configured in DHCP mode.

* BMC credentials should be the same across all servers and provided as input to Omnia.

* Target servers should be configured to boot in PXE mode with appropriate NIC as the first boot device.
