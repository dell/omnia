**Omnia** (Latin: all or everything) is a deployment tool to configure Dell EMC PowerEdge servers running standard RPM-based Linux OS images into clusters capable of supporting HPC, AI, and data analytics workloads. It uses Slurm, Kubernetes, and other packages to manage jobs and run diverse workloads on the same converged solution. It is a collection of [Ansible](https://ansible.com) playbooks, is open source, and is constantly being extended to enable comprehensive workloads.

#### Current release version
1.1.1

#### Previous release version
1.1  

## Blogs about Omnia
- [Introduction to Omnia](https://infohub.delltechnologies.com/p/omnia-open-source-deployment-of-high-performance-clusters-to-run-simulation-ai-and-data-analytics-workloads/)
- [Taming the Accelerator Cambrian Explosion with Omnia](https://infohub.delltechnologies.com/p/taming-the-accelerator-cambrian-explosion-with-omnia/)
- [Containerized HPC Workloads Made Easy with Omnia and Singularity](https://infohub.delltechnologies.com/p/containerized-hpc-workloads-made-easy-with-omnia-and-singularity/)

## What Omnia does
Omnia can build clusters that use Slurm or Kubernetes (or both!) for workload management. Omnia will install software from a variety of sources, including:
- Standard CentOS and [ELRepo](http://elrepo.org) repositories
- Helm repositories
- Source code compilation
- [OperatorHub](https://operatorhub.io)

Whenever possible, Omnia will leverage existing projects rather than reinvent the wheel.

### Omnia stacks
Omnia can install Kubernetes or Slurm (or both), along with additional drivers, services, libraries, and user applications.
![Omnia Kubernetes Stack](images/omnia-k8s.png)

![Omnia Slurm Stack](images/omnia-slurm.png)  

## What's new in this release
* Provisioning of Rocky custom ISO on supported PowerEdge servers using iDRAC.
* Configuring Dell EMC networking switches, Mellanox InfiniBand switches, and PowerVault storage devices in the cluster. 
* An option to configure a login node with the same configurations as the compute nodes in the cluster. With appropriate user privileges provided by the cluster administrator, users can log in to the login node and schedule Slurm jobs. The authentication mechanism in the login node uses the FreeIPA solution.
* Options to enable the security settings on the iDRAC such as system lockdown mode, secure boot mode, 2-factor authentication (2FA), and LDAP directory services.

## Deploying clusters using the Omnia control plane
The Omnia Control Plane will automate the entire cluster deployment process, starting with provisioning the operating system on the supported devices and updating the firmware versions of PowerEdge Servers. 
For detailed instructions, see [Install the Omnia Control Plane](INSTALL_OMNIA_CONTROL_PLANE.md).  

## Installing Omnia to servers with a pre-provisioned OS
Omnia can be deployed on clusters that already have an RPM-based Linux OS running on them and are all connected to the Internet. Currently, all Omnia testing is done on [CentOS](https://centos.org). Please see [Example system designs](EXAMPLE_SYSTEM_DESIGNS.md) for instructions on the network setup.

Once servers have functioning OS and networking, you can use Omnia to install and start Slurm and/or Kubernetes. For detailed instructions, see [Install Omnia using CLI](INSTALL_OMNIA.md). 

# System requirements  
The following table lists the software and operating system requirements on the management station, manager, and compute nodes. To avoid any impact on the proper functioning of Omnia, other versions than those listed are not supported.  

Requirements  |   Version
----------------------------------  |   -------
OS pre-installed on the management station  |  CentOS 8.4/ Rocky 8.4
OS deployed by Omnia on bare-metal Dell EMC PowerEdge Servers | CentOS 7.9 2009 Minimal Edition/ Rocky 8.4 Minimal Edition
Cobbler  |  3.2.2
Ansible AWX  |  19.1.0
Slurm Workload Manager  |  20.11.2
Kubernetes on the management station  |  1.21.0
Kubernetes on the manager and compute nodes	|	1.16.7 or 1.19.3
Kubeflow  |  1
Prometheus  |  2.23.0

## Hardware managed by Omnia
The following table lists the supported devices managed by Omnia. Other devices than those listed in the following table will be discovered by Omnia, but features offered by Omnia will not be applicable.

Device type	|	Supported models	
-----------	|	-------	
Dell EMC PowerEdge Servers	|	PowerEdge C4140, C6420, C6520, R240, R340, R440, R540, R640, R650, R740, R740xd, R740xd2, R750, R750xa, R840, R940, R940xa
Dell EMC PowerVault Storage	|	PowerVault ME4084, ME4024, and ME4012 Storage Arrays
Dell EMC Networking Switches	|	PowerSwitch S3048-ON and PowerSwitch S5232F-ON
Mellanox InfiniBand Switches	|	NVIDIA MQM8700-HS2F Quantum HDR InfiniBand Switch 40 QSFP56


## Software deployed by Omnia
The following table lists the software and its compatible version managed by Omnia. To avoid any impact on the proper functioning of Omnia, other versions than those listed are not supported.

Software	|	License	|	Compatible Version	|	Description
-----------	|	-------	|	----------------	|	-----------------
CentOS Linux release 7.9.2009 (Core)	|	-	|	7.9	|	Operating system on entire cluster except for management station
Rocky 8.4	|	-	|	8.4	|	Operating system on entire cluster except for management station
CentOS Linux release 8.4.2105	|	-	|	8.4	|	Operating system on the management station	
Rocky 8.4	|	-	|	8.4	|	Operating system on the management station
MariaDB	|	GPL 2.0	|	5.5.68	|	Relational database used by Slurm
Slurm	|	GNU General Public	|	20.11.7	|	HPC Workload Manager
Docker CE	|	Apache-2.0	|	20.10.2	|	Docker Service
FreeIPA	|	GNU General Public License v3	|	4.6.8	|	Authentication system used in the login node
OpenSM	|	GNU General Public License 2	|	3.3.24	|	-
NVIDIA container runtime	|	Apache-2.0	|	3.4.2	|	Nvidia container runtime library
Python PIP	|	MIT License	|	21.1.2	|	Python Package
Python3	|	-	|	3.6.8	|	-
Kubelet	|	Apache-2.0	|	1.16.7,1.19,1.21	|	Provides external, versioned ComponentConfig API types for configuring the kubelet
Kubeadm	|	Apache-2.0	|	1.16.7,1.19,1.21	|	"fast paths" for creating Kubernetes clusters
Kubectl	|	Apache-2.0	|	1.16.7,1.19,1.21	|	Command line tool for Kubernetes
JupyterHub	|	Modified BSD License	|	1.1.0	|	Multi-user hub
kubernetes Controllers	|	Apache-2.0	|	1.16.7,1.19,1.21	|	Orchestration tool	
Kfctl	|	Apache-2.0	|	1.0.2	|	CLI for deploying and managing Kubeflow
Kubeflow	|	Apache-2.0	|	1	|	Cloud Native platform for machine learning
Helm	|	Apache-2.0	|	3.5.0	|	Kubernetes Package Manager
Helm Chart	|	-	|	0.9.0	|	-
TensorFlow	|	Apache-2.0	|	2.1.0	|	Machine Learning framework
Horovod	|	Apache-2.0	|	0.21.1	|	Distributed deep learning training framework for Tensorflow
MPI	|	Copyright (c) 2018-2019 Triad National Security,LLC. All rights reserved.	|	0.2.3	|	HPC library
CoreDNS	|	Apache-2.0	|	1.6.2	|	DNS server that chains plugins
CNI	|	Apache-2.0	|	0.3.1	|	Networking for Linux containers
AWX	|	Apache-2.0	|	19.1.0	|	Web-based User Interface
AWX.AWX	|	Apache-2.0	|	19.1.0	|	Galaxy collection to perform awx configuration
AWXkit	|	Apache-2.0	|	to be updated	|	To perform configuration through CLI commands
Cri-o	|	Apache-2.0	|	1.21	|	Container Service
Buildah	|	Apache-2.0	|	1.21.4	|	Tool to build and run container
PostgreSQL	|	Copyright (c) 1996-2020, PostgreSQL Global Development Group	|	10.15	|	Database Management System
Redis	|	BSD-3-Clause License	|	6.0.10	|	In-memory database
NGINX	|	BSD-2-Clause License	|	1.14	|	-
dellemc.openmanage	|	GNU-General Public License v3.0	|	3.5.0	|	It is a systems management and monitoring application that provides a comprehensive view of the Dell EMC servers, chassis, storage, and network switches on the enterprise network
dellemc.os10	|	GNU-General Public License v3.1	|	1.1.1	|	It provides networking hardware abstraction through a common set of APIs
Genisoimage-dnf	|	GPL v3	|	1.1.11	|	Genisoimage is a pre-mastering program for creating ISO-9660 CD-ROM  filesystem images
OMSDK	|	Apache-2.0	|	1.2.456	|	Dell EMC OpenManage Python SDK (OMSDK) is a python library that helps developers and customers to automate the lifecycle management of PowerEdge Servers

# Supported interface keys of PowerSwitch S3048-ON (ToR Switch)
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

# Known issues  
* **Issue**: Hosts are not displayed on the AWX UI.  
	**Resolution**:  
	* Verify if the provisioned_hosts.yml file is present in the omnia/control_plane/roles/collect_node_info/files/ folder.
	* Verify whether the hosts are listed in the provisioned_hosts.yml file.
	* If hosts are not listed, then servers are not PXE booted yet.
If hosts are listed, then an IP address has been assigned to them by DHCP. However, hosts are not displayed on the AWX UI as the PXE boot is still in process or is not initiated.
	* Check for the reachable and unreachable hosts using the provision_report.yml tool present in the omnia/control_plane/tools folder. To run provision_report.yml, in the omnia/control_plane/ directory, run playbook -i roles/collect_node_info/files/provisioned_hosts.yml tools/provision_report.yml.

* **Issue**: There are **ImagePullBack** or **ErrPullImage** errors in the status of Kubernetes pods.  
	**Cause**: The errors occur when the Docker pull limit is exceeded.  
	**Resolution**:
	* For **omnia.yml** and **control_plane.yml**: Provide the docker username and password for the Docker Hub account in the *omnia_config.yml* file and execute the playbook. 
	* For HPC cluster, during omnia.yml execution, a kubernetes secret 'dockerregcred' will be created in default namespace and patched to service account. User needs to patch this secret in their respective namespace while deploying custom applications and use the secret as imagePullSecrets in yaml file to avoid ErrImagePull. [Click here for more info](https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry/)
	* **Note**: If the playbook is already executed and the pods are in __ImagePullBack__ error, then run `kubeadm reset -f` in all the nodes before re-executing the playbook with the docker credentials.

* **Issue**: The `kubectl` command stops working after a reboot and displays the following error message: *The connection to the server head_node_ip:port was refused - did you specify the right host or port?*  
	**Resolution**:
	On the management station or the manager node, run the following commands:  
	* `swapoff -a`
	* `systemctl restart kubelet`  
	
* **Issue**: If control_plane.yml fails at the webui_awx role, then the previous IP address and password are not cleared when control_plane.yml is re-run.   
	**Resolution**: In the *webui_awx/files* directory, delete the *.tower_cli.cfg* and *.tower_vault_key* files, and then re-run `control_plane.yml`.

* **Issue**: The FreeIPA server and client installation fails.  
	**Cause**: The hostnames of the manager and login nodes are not set in the correct format.  
	**Resolution**: If you have enabled the option to install the login node in the cluster, set the hostnames of the nodes in the format: *hostname.domainname*. For example, *manager.omnia.test* is a valid hostname for the login node. **Note**: To find the cause for the failure of the FreeIPA server and client installation, see *ipaserver-install.log* in the manager node or */var/log/ipaclient-install.log* in the login node.  
	
* **Issue**: The inventory details are not updated in AWX when device or host credentials are invalid.  
	**Resolution**: Provide valid credentials of the devices and hosts in the cluster. 

* **Issue**: The Host list is empty after executing the control_plane playbook.  
	**Resolution**: Ensure that all devices used are in DHCP enabled mode.
	
* **Issue**: The task 'Install Packages' fails on the NFS node with the message: `Failure in talking to yum: Cannot find a valid baseurl for repo: base/7/x86_64.`  
	**Cause**: There are connections missing on the NFS node.  
	**Resolution**: Ensure that there are 3 nics being used on the NFS node:
	1. For provisioning the OS
	2. For connecting to the internet (Management purposes)
	3. For connecting to PowerVault (Data Connection)  
	
	
* **Issue**: Hosts are not automatically deleted from awx UI when redeploying the cluster.  
	**Resolution**: Before re-deploying the cluster, ensure that the user manually deletes all hosts from the awx UI.
	
* **Issue**: Decomissioned compute nodes do not get deleted automatically from the awx UI.
	**Resolution**: Once a node is decommisioned, ensure that the user manually deletes decomissioned hosts from the awx UI.

# [Frequently asked questions](FAQ.md)

# Limitations
* Removal of Slurm and Kubernetes component roles are not supported. However, skip tags can be provided at the start of installation to select the component roles.​  
* After installing the Omnia control plane, changing the manager node is not supported. If you need to change the manager node, you must redeploy the entire cluster.  
* Dell Technologies provides support to the Dell-developed modules of Omnia. All the other third-party tools deployed by Omnia are outside the support scope.​
* To change the Kubernetes single node cluster to a multi-node cluster or change a multi-node cluster to a single node cluster, you must either redeploy the entire cluster or run `kubeadm reset -f` on all the nodes of the cluster. You then need to run the *omnia.yml* file and skip the installation of Slurm using the skip tags.  
* In a single node cluster, the login node and Slurm functionalities are not applicable. However, Omnia installs FreeIPA Server and Slurm on the single node.  
* To change the Kubernetes version from 1.16 to 1.19 or 1.19 to 1.16, you must redeploy the entire cluster.  
* The Kubernetes pods will not be able to access the Internet or start when firewalld is enabled on the node. This is a limitation in Kubernetes. So, the firewalld daemon will be disabled on all the nodes as part of omnia.yml execution.

# Contributing to Omnia
The Omnia project was started to give members of the [Dell Technologies HPC Community](https://dellhpc.org) a way to easily set up clusters of Dell EMC servers, and to contribute useful tools, fixes, and functionality back to the HPC Community.

# Open to All
While we started Omnia within the Dell Technologies HPC Community, that doesn't mean that it's limited to Dell EMC servers, networking, and storage. This is an open project, and we want to encourage *everyone* to use and contribute to Omnia!

# Anyone can contribute!
It's not just new features and bug fixes that can be contributed to the Omnia project! Anyone should feel comfortable contributing. We are asking for all types of contributions:
* New feature code
* Bug fixes
* Documentation updates
* Feature suggestions
* Feedback
* Validation that it works for your particular configuration

If you would like to contribute, see [CONTRIBUTING](https://github.com/dellhpc/omnia/blob/release/CONTRIBUTING.md).
