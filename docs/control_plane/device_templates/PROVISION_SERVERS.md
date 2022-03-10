# Custom ISO provisioning on Dell EMC PowerEdge Servers

## Update the input parameters

Edit the following files under the `control_plane/input_params` directory to provide the required input parameters.
1. Edit the `login_vars.yml` file to enter the following details:  
	a. `provision_password`- password used while provisioning OS on bare metal servers.  
	b. `cobbler_password`- password for Cobbler.    
	c. `idrac_username` and `idrac_password`- iDRAC username and password.   
	**NOTE**: Minimum length of the password must be at least eight characters and a maximum of 30 characters. Do not use these characters while entering a password: -, \\, "", and \'
2. Edit the following variables in the `idrac_vars.yml` file.  

	File name	|	Variables</br> [Required/ Optional]	|	Default, choices	|	Description
	-------	|	----------------	|	-----------------	|	-----------------
	idrac_vars.yml	|	idrac_system_profile</br> [Required]	|	<ul><li>**Performance**</li> <li>PerformancePerWatt(DAPC)</li> <li>PerformancePerWatt(OS)</li> <li>WorkstationPerformance</li></ul>	|	The system profile used for BIOS configuration. 
	<br>	|	firmware_update_required</br> [Required]	|	<ul><li>**true**</li> <li>false</li></ul>	|	By default, Omnia updates the firmware on the servers. To disable the firmware update, set the variable to "false".
	<br>	|	poweredge_model</br> [Required if "firmware_update_required" is set to "true"]	|	<ul><li>**C6420**</li> <li>R640</li><li>R740</li><li>C4140</li> <li>And other supported PowerEdge servers</li></ul>	|	Enter the required PowerEdge server models to update the firmware. For example, enter `R640,R740,C4140` to update firmware on these models of PowerEdge servers. For a complete list of supported PowerEdge servers, see the *Hardware managed by Omnia* section in the Readme file.
	<br>	|	uefi_secure_boot</br> [Optional]	|	<ul><li>**disabled**</li> <li>enabled</li></ul>	|	Option to enable or disable the secure boot mode.
	<br>	|	system_lockdown</br> [Optional]	|	<ul><li>**disabled**</li> <li>enabled</li></ul>	|	Option to enable or disable system lockdown.
	<br>	|	two_factor_authentication</br> [Optional]	|	<ul><li>**disabled**</li> <li>enabled</li></ul>	|	Option to enable or disable the 2FA on iDRAC.</br> If enabled, update the required variables in the `idrac_tools_vars.yml` file.</br> **[WARNING]**: For the other iDRAC playbooks to run, you must manually disable 2FA by setting the *Easy 2FA State* to "Disabled" in the iDRAC settings.
	<br>	|	ldap_directory_services</br> [Optional]	|	<ul><li>**disabled**</li> <li>enabled</li></ul>	|	Option to enable or disable the LDAP directory services on iDRAC.</br> If enabled, update the required variables in the `idrac_tools_vars.yml` file.

## Custom ISO file creation for Out-of-band server management
Omnia role used to create the custom ISO: *control_plane_customiso*  
Based on the inputs provided in the `login_vars.yml` and `base_vars.yml` files, the Kickstart file is configured and added to the custom ISO file. The *unattended_centos7.iso*, *unattended_rocky8.iso* or *unattended_leap15.iso* file is copied to an NFS share on the management station to provision the PowerEdge servers using iDRAC. 

## Provisioning of PowerEdge Servers using iDRAC (Out-of-band server management)

### Run idrac_template on the AWX UI.
1. Run `kubectl get svc -n awx`.
2. Copy the Cluster-IP address of the awx-ui. 
3. To retrieve the AWX UI password, run `kubectl get secret awx-admin-password -n awx -o jsonpath="{.data.password}" | base64 --decode`.
4. Open the default web browser on the management station and enter `http://<IP>:8052`, where IP is the awx-ui IP address and 8052 is the awx-ui port number. Log in to the AWX UI using the username as `admin` and the retrieved password.  
5. Under __RESOURCES__ -> __Templates__, launch the **idrac_template**.

Omnia role used to provision custom ISO on PowerEdge Servers using iDRAC: *provision_idrac*  

For the `idrac.yml` file to successfully provision the custom ISO on the PowerEdge Servers, ensure that the following prerequisites are met:
* The **idrac_inventory** file is updated with the iDRAC IP addresses.
* Required input parameters are updated in the **idrac_vars.yml** file under **omnia/control_plane/input_params** directory.
* An *unattended_centos7.iso*, *unattended_rocky8.iso* or *unattended_leap15.iso* file is available in an NFS path.
* The Lifecycle Controller Remote Services of PowerEdge Servers is in the 'ready' state.
* The Redfish services are enabled in the iDRAC settings under **Services**.
* The PowerEdge Servers have the iDRAC Enterprise or Datacenter license. If the license is not found, servers will be PXE booted and provisioned using Cobbler.  

The **provision_idrac** file configures and validates the following:
* Required input parameters and prerequisites.
* BIOS and SNMP settings.
* The latest available version of the iDRAC firmware is updated.
* If bare metal servers have a RAID controller installed, Virtual disks are created for RAID configuration.
* Availability of iDRAC Enterprise or Datacenter License on iDRAC.  

After the configurations are validated, the **provision_idrac** file provisions the custom ISO on the PowerEdge Servers. After the OS is provisioned successfully, iDRAC IP addresses are updated in the *provisioned_idrac_inventory* in AWX.

>>**NOTE**: The `idrac.yml` file initiates the provisioning of custom ISO on the PowerEdge servers. Wait for some time for the node inventory to be updated on the AWX UI. 

### Provisioning newly added PowerEdge servers in the cluster
To provision newly added servers, wait till the iDRAC IP addresses are automatically added to the *idrac_inventory*. After the iDRAC IP addresses are added, launch the iDRAC template on the AWX UI to provision CentOS custom OS on the servers.  

If you want to reprovision all the servers in the cluster or any of the faulty servers, you must remove the respective iDRAC IP addresses from *provisioned_idrac_inventory* on AWX UI and then launch the iDRAC template. If required, you can delete the *provisioned_idrac_inventory* from the AWX UI to remove the IP addresses of provisioned servers. After the servers are provisioned, *provisioned_idrac_inventory* is created and updated on the AWX UI.

## OS provisioning on PowerEdge Servers using Cobbler on the host network  

Omnia role used: *provision_cobbler*  
Ports used by Cobbler:  
* TCP ports: 69,8000, 8008
* UDP ports: 69,4011

To create the Cobbler image, Omnia configures the following:
* Firewall settings.
* The kickstart file of Cobbler to enable the UEFI PXE boot.

To access the Cobbler dashboard, enter `https://<IP>/cobbler_web` where `<IP>` is the Global IP address of the management station. For example, enter
`https://100.98.24.225/cobbler_web` to access the Cobbler dashboard.

>>__Note__: After the Cobbler Server provisions the operating system on the servers, IP addresses and hostnames are assigned by the DHCP service.  
>>* If a mapping file is not provided, the hostname to the server is provided based on the following format: **computexxx-xxx** where "xxx-xxx" is the last two octets of the Host IP address. For example, if the Host IP address is 172.17.0.11 then the assigned hostname by Omnia is compute0-11.  
>>* If a mapping file is provided, the hostnames follow the format provided in the mapping file.  

>>__Note__: If you want to add more nodes, append the new nodes in the existing mapping file. However, do not modify the previous nodes in the mapping file as it may impact the existing cluster.

>> __Note__: With the addition of Multiple profiles, the cobbler container dynamically updates the mount point based on the value of `provision_os` in `base_vars.yml`.

### DHCP routing using Cobbler
Omnia now supports DHCP routing via Cobbler. To enable routing, update the `primary_dns` and `secondary_dns` in `base_vars` with the appropriate IPs (hostnames are currently not supported). For compute nodes that are not directly connected to the internet (ie only host network is configured), this configuration allows for internet connectivity.

## Security enhancements  
Omnia provides the following options to enhance security on the provisioned PowerEdge servers:
* **System lockdown mode**: To enable the system lockdown mode on iDRAC, set the *system_lockdown* variable to "enabled" in the `idrac_vars.yml` file.
* **Secure boot mode**: To enable the secure boot mode on iDRAC, set the *uefi_secure_boot* variable to "enabled" in the `idrac_vars.yml` file.
* **2-factor authentication (2FA)**: To enable the 2FA on iDRAC, set the *two_factor_authentication* variable to "enabled" in the `idrac_vars.yml` file.  
	
	**WARNING**: If 2FA is enabled on iDRAC, you must manually disable 2FA on iDRAC by setting the *Easy 2FA State* to "Disabled" for the user specified in the `login_vars.yml` file to run other iDRAC playbooks. 
	
	Before executing the **idrac_2fa.yml**, you must edit the `idrac_tools_vars.yml` by running the following command: `ansible-vault edit idrac_tools_vars.yml --vault-password-file .idrac_vault_key`.   
	
	Provide the following details in the **idrac_2fa.yml** file.  
	
	File name	|	Variables</br> [Required if two_factor_authentication is enabled/ Optional]	|	Default, choices	|	Description
	-------	|	----------------	|	-----------------	|	-----------------
	idrac_2fa.yml	|	dns_domain_name</br> [Required]	|		|	DNS domain name to be set for iDRAC. 
	<br>	|	ipv4_static_dns1, ipv4_static_dns2</br> [Required] 	|		|	DNS1 and DNS2 static IPv4 addresses.
	<br>	|	smtp_server_ip</br> [Required]	|		|	Server IP address used for SMTP.
	<br>	|	use_email_address_2fa</br> [Required]	|		|	Email address used for enabling 2FA. After 2FA is enabled, an authentication code is sent to the provided email address. 
	<br>	| smtp_authentication [Required]	| <ul> <li>__Disabled__</li> <li>Enabled </li> </ul> | Enable SMTP authentication 
	<br>	|	smtp_username</br> [Optional]	|		|	Username for SMTP.
	<br>	|	smtp_password</br> [Optional]	|		|	Password for SMTP.

	>>**NOTE**: 2FA will be enabled on the iDRAC only if SMTP server details are valid and a test email notification is working using SMTP.  
* **LDAP Directory Services**: To enable or disable the LDAP directory services, set the *ldap_directory_services* variable to "enabled" in the `idrac_vars.yml` file.  

	Before executing the **idrac_ldap.yml** file, you must edit `idrac_tools_vars.yml` by running the following command: `ansible-vault edit idrac_tools_vars.yml --vault-password-file .idrac_vault_key`.  
	
	Provide the following values in the **idrac_ldap.yml** file.  

	File name	|	Variables</br> [Required if ldap_directory_services is enabled/ Optional]	|	Default, choices	|	Description
	-------	|	----------------	|	-----------------	|	-----------------
	idrac_ldap.yml	|	cert_validation_enable</br> [Required]	|	<ul><li>**disabled**</li></ul>	|	This option will be disabled by default. If required, you must manually upload the CA certificate.
	<br>	|	ldap_server_address</br> [Required] 	|		|	Server address used for LDAP.
	<br>	|	ldap_port</br> [Required]	|	<ul><li>636</li></ul>	|	TCP port at which the LDAP server is listening for connections.
	<br>	|	bind_dn</br> [Optional]	|		|	Distinguished Name of the node in your directory tree from which records are searched.
	<br>	|	bind_password</br> [Optional]	|		|	Password used for "bind_dn".
	<br>	|	base_dn</br> [Required]	|		|	Distinguished Name of the search base.
	<br>	|	user_attribute</br> [Optional]	|		|	User attribute used for searching in LDAP server.
	<br>	|	group_attribute</br> [Optional]	|		|	Group attribute used for searching in LDAP server.
	<br>	|	group_attribute_is_dn</br> [Required]	|	<ul><li>**enabled**</li> <li>disabled</li></ul>	|	Specify whether the group attribute type is DN or not.
	<br>	|	search_filter</br> [Optional]	|		|	Search scope is related to the Base DN. 
	<br>	|	role_group1_dn</br> [Required]	|		|	DN of LDAP group to be added.
	<br>	|	role_group1_privilege</br> [Required]	|	<ul><li>**Administrator**</li><li>Operator</li><li>ReadOnly</li></ul>	|	Privilege to LDAP role group 1.  
	
	To view the `idrac_tools_vars.yml` file, run the following command: `ansible-vault view idrac_tools_vars.yml --vault-password-file .idrac_vault_key`  
	
	>>**NOTE**: It is suggested that you use the ansible-vault view or edit commands and that you do not use the ansible-vault decrypt or encrypt commands. If you have used the ansible-vault decrypt or encrypt commands, provide 644 permission to `idrac_tools_vars.yml`.  

On the AWX Dashboard, select the respective security requirement playbook and launch the iDRAC template by performing the following steps.
1. On the AWX Dashboard, under __RESOURCES__ -> __Templates__, select the **idrac_template**.
2. Under the **Details** tab, click **Edit**.
3. In the **Edit Details** page, click the **Playbook** drop-down menu and select **tools/idrac_system_lockdown.yml**, **tools/idrac_secure_boot.yml**, **tools/idrac_2fa.yml**, or **tools/idrac_ldap.yml**.
4. Click **Save**.
5. To launch the iDRAC template with the respective playbook selected, click **Launch**.  

 


