# Configuring Dell EMC PowerSwitches  

## Update the input parameters 
Under the `control_plane/input_params` directory, edit the following files:
1. `base_vars.yml` file: Update the following variable to enable or disable Ethernet switch configurations in the cluster.  

	Variable	|	Default, choices	|	Description
	-------	|	----------------	|	-----------------
	ethernet_switch_support	|	<ul><li>**false**</li><li>true</li></ul>	|	Set the variable to "true" to enable Ethernet switch configurations.  

2. `login_vars.yml` file:  Enter the following details to configure Ethernet switches.  
	a. `ethernet_switch_username`- username for Ethernet switches.  
	**NOTE**: The username must not contain the following characters: -, \\, "", and \'  
	b. `ethernet_switch_password`- password for Ethernet switches.   
	**NOTE**: Minimum length of the password must be eight characters and the maximum limit is 30 characters. Do not use these characters while entering a password: -, \\, "", and \'  

3. `ethernet_tor_vars.yml` or `ethernet_vars.yml` file: If **ethernet_switch_support** is set to "true" in the *base_vars.yml* file, then update the following variables.  

	a. Edit the *ethernet_tor_vars.yml* file for all S3* and S4* PowerSwitches such as S3048-ON, S4048T-ON, S4112F-ON, S4048-ON, S4048T-ON, S4112F-ON, S4112T-ON, and S4128F-ON.  

	Variables	|	Default, choices	|	Description
	----------------	|	-----------------	|	-----------------
	os10_config	|	<ul><li>"interface vlan1"</li><li>"exit"</li></ul>	|	Global configurations for the switch.
	os10_interface	|	By default: <ul><li>Port description is provided.</li> <li>Each interface is set to "up" state.</li>	|	Update the individual interfaces of the PowerSwitch S3048-ON (ToR Switch). </br>The interfaces are from **ethernet 1/1/1** to **ethernet 1/1/52**. For more information about the interfaces, see the *Supported interface keys of PowerSwitch S3048-ON (ToR Switch)* section in the README file. </br>**NOTE**: The playbooks will fail if any invalid configurations are entered.
	save_changes_to_startup	|	<ul><li>**false**</li><li>true</li></ul>	|	Change it to "true" only when you are certain that the updated configurations and commands are valid. </br>**WARNING**: When set to "true", the startup configuration file is updated. If incorrect configurations or commands are entered, the Ethernet switches may not operate as expected.  

	b. Edit the *ethernet_vars.yml* file for Dell PowerSwitch S5232F-ON and all other PowerSwitches except S3* and S4* switches.  
	
	Variables	|	Default, choices	|	Description
	----------------	|	-----------------	|	-----------------
	os10_config	|	<ul><li>"interface vlan1"</li><li>"exit"</li></ul>	|	Global configurations for the switch.  
	breakout_value	|	<ul><li>**10g-4x**</li><li>5g-4x</li><li>40g-1x</li><li>50g-2x</li><li>100g-1x</li></ul>	|	By default, all ports are configured in the 10g-4x breakout mode in which a QSFP28 or QSFP+ port is split into four 10G interfaces. For more information about the breakout modes, see [Configure breakout mode](https://www.dell.com/support/manuals/en-vc/networking-s5296f-on/smartfabric-os-user-guide-10-5-1/configure-breakout-mode?guid=guid-f47a803b-1a3f-44b9-a887-b1d5b395e0cb&lang=en-us).
	os10_interface	|	By default: <ul><li>Port description is provided.</li> <li>Each interface is set to "up" state.</li><li>The *fanout/breakout* mode for 1/1/1 to 1/1/31 is as per the value set in the *breakout_value* variable.</li>	|	Update the individual interfaces of the Dell PowerSwitch S5232F-ON. </br>The interfaces are from **ethernet 1/1/1** to **ethernet 1/1/34**. By default, the breakout mode is set for 1/1/1 to 1/1/31. </br>**NOTE**: The playbooks will fail if any invalid configurations are entered.
	save_changes_to_startup	|	<ul><li>**false**</li><li>true</li></ul>	|	Change it to "true" only when you are certain that the updated configurations and commands are valid. </br>**WARNING**: When set to "true", the startup configuration file is updated. If incorrect configurations or commands are entered, the Ethernet switches may not operate as expected.   
	
## Configuring PowerSwitches

### Run ethernet_template on the AWX UI.
1. Run `kubectl get svc -n awx`.
2. Copy the Cluster-IP address of the awx-ui. 
3. To retrieve the AWX UI password, run `kubectl get secret awx-admin-password -n awx -o jsonpath="{.data.password}" | base64 --decode`.
4. Open the default web browser on the management station and enter `http://<IP>:8052`, where IP is the awx-ui IP address and 8052 is the awx-ui port number. Log in to the AWX UI using the username as `admin` and the retrieved password.  
5. Under __RESOURCES__ -> __Templates__, launch the **ethernet_template**.