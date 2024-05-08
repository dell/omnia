**Hostname requirements**
		* The Hostname should not contain the following characters: , (comma), \. (period) or _ (underscore). However, the **domain name** is allowed commas and periods.
		* The Hostname cannot start or end with a hyphen (-).
		* No upper case characters are allowed in the hostname.
		* The hostname cannot start with a number.
		* The hostname and the domain name (that is: ``hostname00000x.domain.xxx``) cumulatively cannot exceed 64 characters. For example, if the ``node_name`` provided in ``input/provision_config.yml`` is 'node', and the ``domain_name`` provided is 'omnia.test', Omnia will set the hostname of a target cluster  node to 'node00001.omnia.test'. Omnia appends 6 digits to the hostname to individually name each target node.