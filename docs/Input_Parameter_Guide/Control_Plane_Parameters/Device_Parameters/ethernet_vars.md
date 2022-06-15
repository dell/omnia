# Parameters in `ethernet_vars.yml`
This file is located in [/control_plane/input_params](../../../../control_plane/input_params/ethernet_vars.yml)

Variables	|	Default, choices	|	Description
----------------	|	-----------------	|	-----------------
os10_config	|	<ul><li>"interface vlan1"</li><li>"exit"</li></ul>	|	Global configurations for the switch.  
breakout_value	|	<ul><li>**10g-4x**</li><li>5g-4x</li><li>40g-1x</li><li>50g-2x</li><li>100g-1x</li></ul>	|	By default, all ports are configured in the 10g-4x breakout mode in which a QSFP28 or QSFP+ port is split into four 10G interfaces. For more information about the breakout modes, see [Configure breakout mode](https://www.dell.com/support/manuals/en-vc/networking-s5296f-on/smartfabric-os-user-guide-10-5-1/configure-breakout-mode?guid=guid-f47a803b-1a3f-44b9-a887-b1d5b395e0cb&lang=en-us).
os10_interface	|	By default: <ul><li>Port description is provided.</li> <li>Each interface is set to "up" state.</li><li>The *fanout/breakout* mode for 1/1/1 to 1/1/31 is as per the value set in the *breakout_value* variable.</li>	|	Update the individual interfaces of the Dell PowerSwitch S5232F-ON. </br>The interfaces are from **ethernet 1/1/1** to **ethernet 1/1/34**. By default, the breakout mode is set for 1/1/1 to 1/1/31. </br>**Note**: The playbooks will fail if any invalid configurations are entered.
save_changes_to_startup	|	<ul><li>**false**</li><li>true</li></ul>	|	Change it to "true" only when you are certain that the updated configurations and commands are valid. </br>**WARNING**: When set to "true", the startup configuration file is updated. If incorrect configurations or commands are entered, the Ethernet switches may not operate as expected.   
	