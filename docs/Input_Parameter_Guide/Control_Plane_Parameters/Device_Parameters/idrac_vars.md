# Parameters in `idrac_vars.yml`
This file is located in [/control_plane/input_params](../../../../control_plane/input_params/idrac_vars.yml)

|	Variables</br> [Required/ Optional]	|	Default, choices	|	Description
----------------	|	-----------------	|	-----------------
idrac_system_profile</br> [Required]	|	<ul><li>**Performance**</li> <li>PerformancePerWatt(DAPC)</li> <li>PerformancePerWatt(OS)</li> <li>WorkstationPerformance</li></ul>	|	The system profile used for BIOS configuration. 
firmware_update_required</br> [Required]	|	<ul><li>**false**</li> <li>true</li></ul>	|	By default, Omnia updates the firmware on the servers. To disable the firmware update, set the variable to "false".
poweredge_model</br> [Required if "firmware_update_required" is set to "true"]	|	<ul><li>**C6420**</li> <li>R640</li><li>R740</li><li>C4140</li> <li>And other supported PowerEdge servers</li></ul>	|	Enter the required PowerEdge server models to update the firmware. For example, enter `R640,R740,C4140` to update firmware on these models of PowerEdge servers. For a complete list of supported PowerEdge servers, see the *Hardware managed by Omnia* section in the Readme file.
uefi_secure_boot</br> [Optional]	|	<ul><li>**disabled**</li> <li>enabled</li></ul>	|	Option to enable or disable the secure boot mode.
system_lockdown</br> [Optional]	|	<ul><li>**disabled**</li> <li>enabled</li></ul>	|	Option to enable or disable system lockdown.
two_factor_authentication</br> [Optional]	|	<ul><li>**disabled**</li> <li>enabled</li></ul>	|	Option to enable or disable the 2FA on iDRAC.</br> If enabled, update the required variables in the `idrac_tools_vars.yml` file.</br> **[WARNING]**: For the other iDRAC playbooks to run, you must manually disable 2FA by setting the *Easy 2FA State* to "Disabled" in the iDRAC settings.
ldap_directory_services</br> [Optional]	|	<ul><li>**disabled**</li> <li>enabled</li></ul>	|	Option to enable or disable the LDAP directory services on iDRAC.</br> If enabled, update the required variables in the `idrac_tools_vars.yml` file.
