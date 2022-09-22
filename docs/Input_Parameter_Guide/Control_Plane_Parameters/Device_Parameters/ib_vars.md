# Parameters in `ib_vars.yml`
This file is located in [/control_plane/input_params](../../../../control_plane/input_params/ib_vars.yml)

Variables	|	Default, choices	|	Description
----------------	|	-----------------	|	-----------------
cache_directory	|	<ul><li>**/var/cache/opensm**</li><li>User-defined directory path</li></ul>	|	The directory used by opensm to store data during the configuration. Can be set to the default directory or enter a directory path to store data.
log_directory	|	<ul><li>**/var/log**</li><li>User-defined directory path</li></ul>	|	The directory where temporary files of opensm are stored. Can be set to the default directory or enter a directory path to store temporary files.
mellanox_switch_config	|		|	List the configurations for the Mellanox InfiniBand switches. 
mellanox_switch_interface_config	|	By default: <ul><li>Port descriptions are provided.</li> <li>Each interface is set to "no shutdown" state.</li> |	Update the individual interfaces of the Mellanox InfiniBand switches. </br>Default configurations are provided for the *Mellanox Quantum(TM) HDR InfiniBand Switch, 40 QSFP56 ports* switch. The configurations must be changed based on the switch used. Omnia playbooks will work on all switches running MLNX-OS. </br>The interfaces are from **ib 1/1** to **ib 1/36**. For each dict, provide a description and configuration. For more information on the commands, see https://docs.mellanox.com/display/MLNXOSv392302. </br>**Note**: The playbooks will fail if any invalid configurations are entered.
save_changes_to_startup	|	<ul><li>**false**</li><li>true</li></ul>	|	Change it to "true" only when you are certain that the updated configurations and commands are valid. </br>**WARNING**: When set to "true", the startup configuration file is updated. If incorrect configurations or commands are entered, the Mellanox InfiniBand band switches may not operate as expected.  
