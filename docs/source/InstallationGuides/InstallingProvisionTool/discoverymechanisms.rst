Discovery Mechanisms
-----------------------

Depending on the value of ``discovery_mechanism`` in ``input/provision_config.yml``, potential target servers can be discovered one of three ways:
	
	Mapping File
	+++++++++++++
	
		To dictate IP address/MAC mapping, a host mapping file can be provided. If the mapping file is not provided and the variable is left blank, a default mapping file will be created by querying the switch. Use the `pxe_mapping_file.csv <../../Samplefiles.html>`_ to create your own mapping file.
	BMC
	++++
	
		Using ```` and ````, an IP range can be 