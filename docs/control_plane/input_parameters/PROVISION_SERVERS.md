# Dell EMC PowerEdge Servers

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

## Deploy Omnia Control Plane
Before you provision the Dell EMC PowerEdge Servers, you must complete the deployment of Omnia control plane. Go to Step 8 in the [Steps to install the Omnia Control Plane](../../INSTALL_OMNIA_CONTROL_PLANE.md#steps-to-deploy-the-omnia-control-plane) file to run the `ansible-playbook control_plane.yml` file.

