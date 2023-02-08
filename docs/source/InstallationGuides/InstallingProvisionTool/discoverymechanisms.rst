Discovery Mechanisms
-----------------------

Depending on the value of ``discovery_mechanism`` in ``input/provision_config.yml``, potential target servers can be discovered one of three ways:
	
Mapping File
+++++++++++++
	
    To provision via mapping file, the following information has to be provided:

    - ``pxe_mapping_file

BMC
++++

    To provision via BMC (IPMI), the following information has to be provided:

    - ``bmc_dynamic_start_range/bmc_dynamic_end_range``: The dhcp range for assigning the IPv4 address while discovery mechanism is BMC.
    - ``bmc_static_start_range/bmc_static_end_range``: The static range for assigning the IPv4 address while discovery mechanism is BMC.
    - ``omnia_exclusive_static_start_range/omnia_exclusive_static_end_range``: The static range of IPs exclusively leased to Omnia to maintain the BMC DHCP range.
    - ``bmc_username``: Provide the iDRAC username here.
    - ``bmc_password``: Provide the iDRAC password here.
    - ``pxe_subnet``: The subnet within with PXE provisioning is done.

SNMP
++++
    To provision via SNMP, the following information has to be provided:

    - ``pxe_switch_ip``: The SNMP enabled switch to be used for discovery.
    - ``pxe_switch_snmp_community_string``: The SNMP community string used to access statistics, MAC addresses and IPs stored within a router or other device.
    - ``bmc_nic_subnet``: The subnet within which IPs are to be assigned.
