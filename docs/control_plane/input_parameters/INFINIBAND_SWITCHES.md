# Mellanox InfiniBand Switches  
In your HPC cluster, Mellanox InfiniBand switches must be connected using the Fat-Tree topology. In the fat-tree topology, switches in layer 1 are connected through the switches in the upper layer-layer 2. And, all the compute nodes in the cluster such as PowerEdge servers and PowerVault storage devices are connected to switches in layer 1. With this topology in place, we are ensuring that a 1x1 communication path is established between the compute nodes. For more information on the fat-tree topology, see https://community.mellanox.com/s/article/designing-an-hpc-cluster-with-mellanox-infiniband-solutions.

Omnia uses the server-based Subnet Manager (SM) where the SM runs as a Kubernetes pod on the management station. To enable the SM, Omnia configures the required parameters in the `opensm.conf` file. These parameters can be edited based on the requirement to enable the SM on the Mellanox InfiniBand Switches.  

**NOTE**: Install the InfiniBand hardware drivers by running the command: `yum groupinstall "Infiniband Support" -y`.  

## Edit the "input_params" file 
Under the `control_plane/input_params` directory, edit the following files:  

1. Edit the following variables in the `base_vars.yml` file.  

File name	|	Variables	|	Default, choices	|	Description
-----------	|	-------	|	----------------	|	-----------------
base_vars.yml	|	ib_switch_support	|	<ul><li>**false**</li><li>true</li></ul>	|	To enable Mellanox InfiniBand switch configuration, set the variable to "true".
<br>	|	ib_network_nic	|	<ul><li>**ib0**</li></ul>	|	NIC or Ethernet card that must be connected to configure Mellanox InfiniBand switches.  
<br>	|	ib_network_dhcp_start_range, ib_network_dhcp_end_range	|		|	DHCP range for the DHCP server to assign IPv4 addresses.

2. Edit the `login_vars.yml` file to enter the following details:  
	a. `ib_username` and `ib_password`- username and password for InfiniBand Switches.   
	**NOTE**: Minimum length of the password must be at least eight characters and a maximum of 30 characters. Do not use these characters while entering a password: -, \\, "", and \'
	
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

## Deploy Omnia Control Plane
Before you configure the Mellanox InfiniBand switches, you must complete the deployment of Omnia control plane. Go to Step 8 in the [Steps to install the Omnia Control Plane](../../INSTALL_OMNIA_CONTROL_PLANE.md#steps-to-deploy-the-omnia-control-plane) file to run the `ansible-playbook control_plane.yml` file.  