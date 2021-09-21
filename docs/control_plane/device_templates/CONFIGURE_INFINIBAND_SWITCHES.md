# Configuring Mellanox InfiniBand Switches  
In your HPC cluster, connect the Mellanox InfiniBand switches using the Fat-Tree topology. In the fat-tree topology, switches in layer 1 are connected through the switches in the upper layer, i.e., layer 2. And, all the compute nodes in the cluster, such as PowerEdge servers and PowerVault storage devices, are connected to switches in layer 1. With this topology in place, we ensure that a 1x1 communication path is established between the compute nodes. For more information on the fat-tree topology, see https://community.mellanox.com/s/article/designing-an-hpc-cluster-with-mellanox-infiniband-solutions.

Omnia uses the server-based Subnet Manager (SM). SM runs as a Kubernetes pod on the management station. To enable the SM, Omnia configures the required parameters in the `opensm.conf` file. Based on the requirement, the parameters can be edited.  

>>**NOTE**: Install the InfiniBand hardware drivers by running the command: `yum groupinstall "Infiniband Support" -y`.  

## Setting up a new or factory reset switch

When connecting to a new or factory reset switch, the configuration wizard requests to execute an initial configuration:
* **(Recommended)** If the user enters 'no', they still have to provide the admin and monitor passwords. 
* If the user enters 'yes', they will also be prompted to enter the hostname for the switch, DHCP details, IPv6 details, etc.

>> **Note:** When initializing a factory reset switch, the user needs to ensure DHCP is enabled and an IPv6 address is not assigned. Omnia will assign an IP address to the Infiniband switch using DHCP with all other configurations.

## Edit the "input_params" file 
Under the `control_plane/input_params` directory, edit the following files:  

1. `base_vars.yml` file    

	File name	|	Variables	|	Default, choices	|	Description
	-----------	|	-------	|	----------------	|	-----------------
	base_vars.yml	|	ib_switch_support	|	<ul><li>**false**</li><li>true</li></ul>	|	To enable Mellanox InfiniBand switch configuration, set the variable to "true".
	<br>	|	ib_network_nic	|	<ul><li>**ib0**</li></ul>	|	NIC or Ethernet card that must be connected to configure Mellanox InfiniBand switches.  
	<br>	|	ib_network_dhcp_start_range, ib_network_dhcp_end_range	|		|	DHCP range for the DHCP server to assign IPv4 addresses.
	
2. `login_vars.yml` file  
	a. `ib_username` and `ib_password`- username and password for InfiniBand Switches.   
	**NOTE**: Minimum length of the password must be eight characters and maximum of 30 characters. Do not use these characters while entering a password: -, \\, "", and \'
	
## Configuring the Subnet Manager on the management station
By default, Omnia enables and configures the Subnet Manager with the default attributes.  
1. [Optional step] If you want to change the attributes of the Subnet Manager, under `control_plane/input_params`, edit the `opensm.conf` file.  
2. Under `control_plane/input_params`, the following variables are provided in the `ib_vars` file.   

	Variables	|	Default, choices	|	Description
	----------------	|	-----------------	|	-----------------
	cache_directory	|	<ul><li>**/var/cache/opensm**</li><li>User-defined directory path</li></ul>	|	The directory used by opensm to store data during the configuration. Can be set to the default directory or enter a directory path to store data.
	log_directory	|	<ul><li>**/var/log**</li><li>User-defined directory path</li></ul>	|	The directory where temporary files of opensm are stored. Can be set to the default directory or enter a directory path to store temporary files.
	mellanox_switch_config	|		|	List the configurations for the Mellanox InfiniBand switches. 
	mellanox_switch_interface_config	|	By default: <ul><li>Port descriptions are provided.</li> <li>Each interface is set to "no shutdown" state.</li> |	Update the individual interfaces of the Mellanox InfiniBand switches. </br>Default configurations are provided for the *Switch-IB(TM) 2 based EDR InfiniBand 1U Switch, 36 QSFP28 ports* switch. The configurations must be changed based on the switch used. Omnia playbooks will work on all switches running MLNX-OS. </br>The interfaces are from **ib 1/1** to **ib 1/36**. For each dict, provide a description and configuration. For more information on the commands, see https://docs.mellanox.com/display/MLNXOSv392302. </br>**NOTE**: The playbooks will fail if any invalid configurations are entered.
	save_changes_to_startup	|	<ul><li>**false**</li><li>true</li></ul>	|	Change it to "true" only when you are certain that the updated configurations and commands are valid. </br>**WARNING**: When set to "true", the startup configuration file is updated. If incorrect configurations or commands are entered, the Mellanox InfiniBand band switches may not operate as expected.   

## Configuring Mellanox InfiniBand Switches

### Run infiniband_template on the AWX UI.
1. Run `kubectl get svc -n awx`.
2. Copy the Cluster-IP address of the awx-ui. 
3. To retrieve the AWX UI password, run `kubectl get secret awx-admin-password -n awx -o jsonpath="{.data.password}" | base64 --decode`.
4. Open the default web browser on the management station and enter `http://<IP>:8052`, where IP is the awx-ui IP address and 8052 is the awx-ui port number. Log in to the AWX UI using the username as `admin` and the retrieved password.  
5. Under __RESOURCES__ -> __Templates__, launch the **infiniband_template**.
