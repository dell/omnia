**Hostname requirements**
        * In the  ``omnia/examples`` folder, a **mapping_host_file.csv** template is provided which can be used for DHCP configuration. The header in the template file must not be deleted before saving the file. It is recommended to provide this optional file as it allows IP assignments provided by Omnia to be persistent across control plane reboots.
    	* The Hostname should not contain the following characters: , (comma), \. (period) or _ (underscore). However, the **domain name** is allowed commas and periods.
    	* The Hostname cannot start or end with a hyphen (-).
    	* No upper case characters are allowed in the hostname.
    	* The hostname cannot start with a number.