# Parameters in `powervault_me4_vars.yml`
This file is located in [/control_plane/input_params](../../../control_plane/input_params/powervault_me4_vars.yml)

Variables	|	Default, choices	|	Description
----------------	|	-----------------	|	-----------------
locale	|	<ul><li>English</li></ul>	|	Represents the selected language. Currently, only English is supported.
powervault_me4_system_name [Optional]	|	<ul><li>**Uninitialized_Name**</li><li>User-defined name</li></ul>	|	The system name used to identify the PowerVault Storage device. The name should be less than 30 characters and must not contain spaces.
powervault_me4_snmp_notify_level [Required]	|	<ul><li>**none**</li><li>crit</li><li>error</li><li>warn</li><li>resolved</li><li>info</li></ul>	|	Select the SNMP notification levels for PowerVault Storage devices. 
powervault_me4_raid_levels	[Required] |	<ul><li>**raid1**</li>Examples:<li>r5/raid5: 3-16</li><li>r6/raid6: 4-16</li><li>r10/raid10: 4-16</li><li>adapt: 12-128</li></ul> |	Enter the required RAID levels and the minimum and maximum number of disks for each RAID levels.
powervault_me4_disk_range	[Required]	|	<ul><li>0.1-2</li></ul>	|	Enter the range of disks in the format *enclosure-number.disk-range,enclosure-number.disk-range*. For example, to select disks 3 to 12 in enclosure 1 and to select disks 5 to 23 in enclosure 2, you must enter `1.3-12, 2.5-23`. </br>A RAID 10 or 50 disk group with disks in subgroups are separated by colons (with no spaces). RAID-10 example:1.1-2:1.3-4:1.7,1.10 </br>**Note**: Ensure that the entered disk location is empty and the **Usage** column lists the range as **AVAIL**. The disk range specified must be of the same vendor and they must have the same description.  
powervault_me4_k8s_volume_name [Required] |	<ul><li>**k8s_volume**</li><li>User-defined name</li></ul> |	Enter the Kubernetes volume name.	
powervault_me4_slurm_volume_name [Required] |	<ul><li>**slurm_volume**</li><li>User-defined name</li></ul> |	Enter the Slurm volume name.
powervault_me4_disk_group_name |	<ul><li>**omnia**</li><li>User-defined name</li></ul> |	Enter the group name of the disk.
powervault_me4_disk_partition_size [Required] |	<ul><li>**5**</li><li>Any value between 5-90</li></ul> |	Enter the partition size which would be used as an NFS share.  
powervault_me4_volume_size [Required] |	<ul><li>**100GB**</li><li>Custom value</li></ul> |	Enter the volume size in the format: *SizeTB*, *SizeGB*, *SizeMB*, or *SizeB*.  
powervault_me4_pool [Required] |	<ul><li>**a** (or A)</li><li>b (or B)</li></ul> |	Enter the pool for the volume.
powervault_me4_pool_type [Required] |	<ul><li>Virtual</li><li>**Linear** </li></ul> |	Select the type of pool to be deployed on PowerVault. Ensure that all pools on the device are exclusively virtual or linear.
powervault_me4_server_nic [Required] |	<ul><li>**eno1**</li></ul> |	Enter the NIC of the server to which the PowerVault Storage is connected.
		