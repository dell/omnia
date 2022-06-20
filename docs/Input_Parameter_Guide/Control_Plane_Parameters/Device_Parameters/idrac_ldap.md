# Parameters in `idrac_ldap.yml`
This file is located in [/control_plane/tools](../../../../control_plane/tools/idrac_ldap.yml)

|	Variables</br> [Required if ldap_directory_services is enabled/ Optional]	|	Default, choices	|	Description
----------------	|	-----------------	|	-----------------
cert_validation_enable</br> [Required]	|	<ul><li>**disabled**</li></ul>	|	This option will be disabled by default. If required, you must manually upload the CA certificate.
ldap_server_address</br> [Required] 	|		|	Server address used for LDAP.
ldap_port</br> [Required]	|	<ul><li>636</li></ul>	|	TCP port at which the LDAP server is listening for connections.
bind_dn</br> [Optional]	|		|	Distinguished Name of the node in your directory tree from which records are searched.
bind_password</br> [Optional]	|		|	Password used for "bind_dn".
base_dn</br> [Required]	|		|	Distinguished Name of the search base.
user_attribute</br> [Optional]	|		|	User attribute used for searching in LDAP server.
group_attribute</br> [Optional]	|		|	Group attribute used for searching in LDAP server.
group_attribute_is_dn</br> [Required]	|	<ul><li>**enabled**</li> <li>disabled</li></ul>	|	Specify whether the group attribute type is DN or not.
search_filter</br> [Optional]	|		|	Search scope is related to the Base DN. 
role_group1_dn</br> [Required]	|		|	DN of LDAP group to be added.
role_group1_privilege</br> [Required]	|	<ul><li>**Administrator**</li><li>Operator</li><li>ReadOnly</li></ul>	|	Privilege to LDAP role group 1.  
	