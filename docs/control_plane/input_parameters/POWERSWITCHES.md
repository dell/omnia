# Dell EMC PowerSwitches  

## Update the input parameters 
Under the `control_plane/input_params` directory, edit the following files:
1. `base_vars.yml` file: Update the following variable to enable or disable Ethernet switch configurations in the cluster.  

	Variable	|	Default, choices	|	Description
	-------	|	----------------	|	-----------------
	ethernet_switch_support	|	<ul><li>false</li><li>**true**</li></ul>	|	Set the variable to "true" to enable Ethernet switch configurations.  

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
	
## Supported interface keys of PowerSwitch S3048-ON (ToR Switch)
The following table provides details about the interface keys supported by the S3048-ON ToR Switch. Dell EMC Networking OS10 Enterprise Edition is the supported operating system.

Interface key name	|	Type	|	Description
---------	|   ----	|	-----------
desc	|	string	|	Configures a single line interface description
portmode	|	string	|	Configures port mode according to the device type
switchport	|	boolean: true, false*	|	Configures an interface in L2 mode
admin	|	string: up, down*	|	Configures the administrative state for the interface; configuring the value as administratively "up" enables the interface; configuring the value as administratively "down" disables the interface
mtu	|	integer	|	Configures the MTU size for L2 and L3 interfaces (1280 to 65535)
speed	|	string: auto, 1000, 10000, 25000, ...	|	Configures the speed of the interface
fanout	|	string: dual, single; string:10g-4x, 40g-1x, 25g-4x, 100g-1x, 50g-2x (os10)	|	Configures fanout to the appropriate value
suppress_ra	|	string: present, absent	|	Configures IPv6 router advertisements if set to present
ip_type_dynamic	|	boolean: true, false	|	Configures IP address DHCP if set to true (ip_and_mask is ignored if set to true)
ipv6_type_dynamic	|	boolean: true, false	|	Configures an IPv6 address for DHCP if set to true (ipv6_and_mask is ignored if set to true)
ipv6_autoconfig	|	boolean: true, false	|	Configures stateless configuration of IPv6 addresses if set to true (ipv6_and_mask is ignored if set to true)
vrf	|	string	|	Configures the specified VRF to be associated to the interface
min_ra	|	string	|	Configures RA minimum interval time period
max_ra	|	string	|	Configures RA maximum interval time period
ip_and_mask	|	string	|	Configures the specified IP address to the interface
ipv6_and_mask	|	string	|	Configures a specified IPv6 address to the interface
virtual_gateway_ip	|	string	|	Configures an anycast gateway IP address for a VXLAN virtual network as well as VLAN interfaces
virtual_gateway_ipv6	|	string	|	Configures an anycast gateway IPv6 address for VLAN interfaces
state_ipv6	|	string: absent, present*	|	Deletes the IPV6 address if set to absent
ip_helper	|	list	|	Configures DHCP server address objects (see ip_helper.*)
ip_helper.ip	|	string (required)	|	Configures the IPv4 address of the DHCP server (A.B.C.D format)
ip_helper.state	|	string: absent, present*	|	Deletes the IP helper address if set to absent
flowcontrol	|	dictionary	|	Configures the flowcontrol attribute (see flowcontrol.*)
flowcontrol.mode	|	string: receive, transmit	|	Configures the flowcontrol mode
flowcontrol.enable	|	string: on, off	|	Configures the flowcontrol mode on
flowcontrol.state	|	string: absent, present	|	Deletes the flowcontrol if set to absent
ipv6_bgp_unnum	|	dictionary	|	Configures the IPv6 BGP unnum attributes (see ipv6_bgp_unnum.*) below
ipv6_bgp_unnum.state	|	string: absent, present*	|	Disables auto discovery of BGP unnumbered peer if set to absent
ipv6_bgp_unnum.peergroup_type	|	string: ebgp, ibgp	|	Specifies the type of template to inherit from
stp_rpvst_default_behaviour	|	boolean: false, true	|	Configures RPVST default behavior of BPDU's when set to True, which is default

* *(Asterisk) denotes the default value.

	
## Deploy Omnia Control Plane
Before you configure the Dell EMC PowerSwitches, you must complete the deployment of Omnia control plane. Go to Step 8 in the [Steps to install the Omnia Control Plane](../../INSTALL_OMNIA_CONTROL_PLANE.md#steps-to-deploy-the-omnia-control-plane) file to run the `ansible-playbook control_plane.yml` file.  
