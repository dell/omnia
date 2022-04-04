**Omnia** (Latin: all or everything) is a deployment tool to configure Dell EMC PowerEdge servers running standard RPM-based Linux OS images into clusters capable of supporting HPC, AI, and data analytics workloads. It uses Slurm, Kubernetes, and other packages to manage jobs and run diverse workloads on the same converged solution. It is a collection of [Ansible](https://ansible.com) playbooks, is open source, and is constantly being extended to enable comprehensive workloads.

#### Current release version
1.2

#### Previous release version
1.1.2

## Blogs about Omnia
- [Introduction to Omnia](https://infohub.delltechnologies.com/p/omnia-open-source-deployment-of-high-performance-clusters-to-run-simulation-ai-and-data-analytics-workloads/)
- [Taming the Accelerator Cambrian Explosion with Omnia](https://infohub.delltechnologies.com/p/taming-the-accelerator-cambrian-explosion-with-omnia/)
- [Containerized HPC Workloads Made Easy with Omnia and Singularity](https://infohub.delltechnologies.com/p/containerized-hpc-workloads-made-easy-with-omnia-and-singularity/)
- [Solution Overview: Dell EMC Omnia Software](https://infohub.delltechnologies.com/section-assets/omnia-solution-overview)
- [Solution Brief: Omnia Software](https://infohub.delltechnologies.com/section-assets/omnia-solution-brief)

## What Omnia does
Omnia can build clusters that use Slurm or Kubernetes (or both!) for workload management. Omnia will install software from a variety of sources, including:
- Helm repositories
- Source code compilation
- [OperatorHub](https://operatorhub.io)

Whenever possible, Omnia will leverage existing projects rather than reinvent the wheel.

### Omnia stacks
Omnia can deploy firmware, install Kubernetes or Slurm (or both), along with additional drivers, services, libraries, and user applications.
![Omnia Kubernetes Stack](images/omnia-k8s.png)

![Omnia Slurm Stack](images/omnia-slurm.png)  

## What's new in this release
- Support for Rocky 8.x with latest python/ansible on the Management Station
- Support for Leap 15.3 on the cluster
- Support for Rocky 8.x on the cluster
- Added Grafana integration for better monitoring capability
- Added Loki Log aggregation of Var Logs
- Added Slurm/K8s Monitoring capability
- Added security features to comply with NIST 800-53 Revision 5 and 800-171 Revision 5
- Added the ability to collect telemetry information from SLURM and iDRAC
- Added Grafana plugins to view real time graphs of cluster/node statistics

## Deploying clusters using the Omnia control plane
The Omnia Control Plane will automate the entire cluster deployment process, starting with provisioning the operating system on the supported devices and updating the firmware versions of PowerEdge Servers. 
For detailed instructions, see [Install the Omnia Control Plane](INSTALL_OMNIA_CONTROL_PLANE.md).  

## Installing Omnia to servers with a pre-provisioned OS
Omnia can be deployed on clusters that already have an RPM-based Linux OS running on them and are all connected to the Internet. Currently, all Omnia testing is done using the software versions mentioned [here](README.md#System-requirements ). Please see [Example system designs](EXAMPLE_SYSTEM_DESIGNS.md) for instructions on the network setup.

Once servers have functioning OS and networking, you can use Omnia to install and start Slurm and/or Kubernetes. For detailed instructions, see [Install Omnia using CLI](INSTALL_OMNIA.md). 

# System requirements  
The following table lists the software and operating system requirements on the management station, manager, and compute nodes. To avoid any impact on the proper functioning of Omnia, other versions than those listed are not supported.  

Requirements  |   Version
----------------------------------  |   -------
OS pre-installed on the management station  |  Rocky 8.x
OS deployed by Omnia on bare-metal Dell EMC PowerEdge Servers | Rocky 8.x Minimal Edition/ Leap 15.x
Ansible  |  2.9.21
Python  |  3.6.15

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

| Software	                                  	| 	License	                                                                    | 	Compatible Version	                            | 	Description                                                                                                                                                 |
|-------------------------------------------	|-----------------------------------------------------------------------------	|-------------------------------------------------	|--------------------------------------------------------------------------------------------------------------------------------------------------------------	|
| LeapOS 15.3	                               	| 	-	                                                                        | 	15.x                                            | 	Operating system on entire cluster                                                                                                                          |
| CentOS Linux release 7.9.2009 (Core)	      	| 	-	                                                                        | 	7.9	                                            | 	Operating system on entire cluster except for management station                                                                                            |
| Rocky 8.x	                                 	| 	-	                                                                        | 	8.x	                                            | 	Operating system on entire cluster except for management station                                                                                            |
| Rocky 8.x	                                 	| 	-	                                                                        | 	8.x	                                            | 	Operating system on the management station                                                                                                                  |
| MariaDB	                                   	| 	GPL 2.0	                                                                    | 	5.5.68	                                        | 	Relational database used by Slurm                                                                                                                           |
| Slurm	                                     	| 	GNU General Public	                                                        | 	20.11.7	                                        | 	HPC Workload Manager                                                                                                                                        |
| Docker CE	                                 	| 	Apache-2.0	                                                                | 	20.10.2	                                        | 	Docker Service                                                                                                                                              |
| FreeIPA	                                   	| 	GNU General Public License v3	                                            | 	4.6.8	                                        | 	Authentication system used in the login node                                                                                                                |
| OpenSM	                                    | 	GNU General Public License 2	                                            | 	3.3.24	                                        | 	-                                                                                                                                                           |
| NVIDIA container runtime	                  	| 	Apache-2.0	                                                                | 	3.4.2	                                        | 	Nvidia container runtime library                                                                                                                            |
| Python PIP	                                | 	MIT License	                                                                | 	21.1.2	                                        | 	Python Package                                                                                                                                              |
| Python3	                                   	| 	-	                                                                        | 	3.6.8 (3.6.15 if LeapOS is being used)	        | 	-                                                                                                                                                           |
| Kubelet	                                   	| 	Apache-2.0	                                                                | 	1.16.7,1.19, 1.21  	                            | 	Provides external, versioned ComponentConfig API types for configuring   the kubelet                                                                        |
| Kubeadm	                                   	| 	Apache-2.0	                                                                | 	1.16.7,1.19, 1.21 	                            | 	"fast paths" for creating Kubernetes clusters                                                                                                               |
| Kubectl	                                   	| 	Apache-2.0	                                                                | 	1.16.7,1.19, 1.21 	                            | 	Command line tool for Kubernetes                                                                                                                            |
| kubernetes.core	                           	| 	GPL 3.0	                                                                    | 	2.2.3 	                                        | 	Performs CRUD operations on K8s onjects                                                                                                                     |
| JupyterHub	                                | 	Modified BSD License	                                                    | 	1.1.0	                                        | 	Multi-user hub                                                                                                                                              |
| kubernetes Controllers	                    | 	Apache-2.0	                                                                | 	1.16.7,1.19 (1.21 if LeapOS is being used)	    | 	Orchestration tool	                                                                                                                                        |
| Kfctl	                                     	| 	Apache-2.0	                                                                | 	1.0.2	                                        | 	CLI for deploying and managing Kubeflow                                                                                                                     |
| Kubeflow	                                  	| 	Apache-2.0	                                                                | 	1	                                            | 	Cloud Native platform for machine learning                                                                                                                  |
| Helm	                                      	| 	Apache-2.0	                                                                | 	3.5.0	                                        | 	Kubernetes Package Manager                                                                                                                                  |
| Helm Chart	                                | 	-	                                                                        | 	0.9.0	                                        | 	-                                                                                                                                                           |
| TensorFlow	                                | 	Apache-2.0	                                                                | 	2.1.0	                                        | 	Machine Learning framework                                                                                                                                  |
| Horovod	                                   	| 	Apache-2.0	                                                                | 	0.21.1	                                        | 	Distributed deep learning training framework for Tensorflow                                                                                                 |
| MPI	                                       	| 	Copyright (c) 2018-2019 Triad National Security,LLC. All rights   reserved.	| 	0.3.0	                                        | 	HPC library                                                                                                                                                 |
| CoreDNS	                                   	| 	Apache-2.0	                                                                | 	1.6.2	                                        | 	DNS server that chains plugins                                                                                                                              |
| CNI	                                       	| 	Apache-2.0	                                                                | 	0.3.1	                                        | 	Networking for Linux containers                                                                                                                             |
| AWX	                                       	| 	Apache-2.0	                                                                | 	20.0.0	                                        | 	Web-based User Interface                                                                                                                                    |
| AWX.AWX	                                   	| 	Apache-2.0	                                                                | 	19.4.0	                                        | 	Galaxy collection to perform awx configuration                                                                                                              |
| AWXkit	                                    | 	Apache-2.0	                                                                | 	18.0.0	                                        | 	To perform configuration through CLI commands                                                                                                               |
| CRI-O	                                     	| 	Apache-2.0	                                                                | 	1.21, 1.22.0  									| 	Container Service                                                                                                                                           |
| Buildah	                                   	| 	Apache-2.0	                                                                | 	1.22.4	                                        | 	Tool to build and run containers                                                                                                                            |
| PostgreSQL	                                | 	Copyright (c) 1996-2020, PostgreSQL Global Development Group	            | 	10.15	                                        | 	Database Management System                                                                                                                                  |
| Redis	                                     	| 	BSD-3-Clause License	                                                    | 	6.0.10	                                        | 	In-memory database                                                                                                                                          |
| NGINX	                                     	| 	BSD-2-Clause License	                                                    | 	1.14	                                        | 	-                                                                                                                                                           |
| dellemc.os10	                              	| 	GNU-General Public License v3.1	                                            | 	1.1.1	                                        | 	It provides networking hardware abstraction through a common set of APIs                                                                                    |
| grafana	                                   	| 	Apache-2.0	                                                                | 	8.3.2	                                        | 	Grafana is the open source analytics & monitoring solution for every   database.                                                                            |
| community.grafana	                         	| 	GPL 3.0	                                                                    | 	1.3.0	                                        | 	Technical Support for open source grafana                                                                                                                   |
| OMSDK	                                     	| 	Apache-2.0	                                                                | 	1.2.488	                                        | 	Dell EMC OpenManage Python SDK (OMSDK) is a python library that helps   developers and customers to automate the lifecycle management of PowerEdge   Servers|
| activemq	                                  	| 	Apache-2.0	                                                                | 	5.10.0	                                        | 	Most popular multi protocol, message broker                                                                                                                 |
|  Loki                                     	|  Apache License 2.0                                                         	|  2.4.1                                          	|  Loki is a log aggregation   system   designed to store and query   logs from all your applications and     infrastructure                                   	|
|  Promtail                                 	|  Apache License 2.1                                                         	|  2.4.1                                          	|  Promtail is an agent which ships   the contents of local logs to   a   private Grafana Loki instance or Grafana Cloud.                                      	|
|  kube-prometheus-stack                    	|  Apache License 2.2                                                         	|  25.0.0                                         	|  Kube Prometheus Stack is a   collection of Kubernetes manifests,     Grafana dashboards, and Prometheus rules.                                              	|
|  mailx                                    	|  MIT License                                                                	|  12.5                                           	|  mailx is a Unix utility program   for sending and receiving   mail.                                                                                         	|
|  postfix                                  	|  IBM Public License                                                         	|  3.5.8                                          	|  Mail Transfer Agent (MTA) designed   to determine routes and   send   emails                                                                                	|
|  xorriso                                  	|  GPL version 3                                                              	|  1.4.8                                          	|  xorriso copies file objects from   POSIX compliant filesystems   into Rock   Ridge enhanced ISO 9660 filesystems.                                           	|
|  Dell EMC     OpenManage Ansible Modules  	|  GNU- General Public License   v3.0                                         	|  5.0.0                                          	|  OpenManage Ansible Modules   simplifies and automates     provisioning, deployment, and updates of PowerEdge servers and   modular   infrastructure.        	|
|  389-ds                                   	|  GPL version 3                                                              	|  1.4.4                                          	|   LDAP server used for   authentication, access control.                                                                                                     	|
|  sssd                                     	|  GPL version 3                                                              	|  1.16.1                                         	|  A set of daemons used to manage   access to remote directory services and authentication mechanisms.                                                        	|
|  krb5                                     	|  MIT License                                                                	|  1.19.2                                         	|  Authentication protocol providing   strong authentication for client/server applications by using secret-key   cryptography                                 	|
|  openshift                                	|  Apache 2.0                                                                 	|  0.12.1                                         	|  an on-premises  platform as a   service built around Linux containers orchestrated and managed   by Kubernetes                                              	|
| golang                                    	| BSD-3-Clause License                                                        	| 1.17                                            	| Go is a statically typed, compiled programming language designed at   Google                                                                                 	|
| mysql                                     	| GPL 2.0                                                                     	| 8                                               	| MySQL is an open-source relational database management system.                                                                                               	|
| postgresSQL                               	| PostgresSQL License                                                         	| 12                                              	| PostgreSQL, also known as Postgres, is a free and open-source relational   database management system emphasizing extensibility and SQL compliance.          	|
| idrac-telemetry-reference tools           	| Apache-2.0                                                                  	| 0.1                                             	| Reference toolset for PowerEdge telemetry metric collection and   integration with analytics and visualization solutions.                                    	|
| jansson                                   	| MIT License                                                                 	| 2.14                                            	| C library for encoding, decoding and manipulating JSON data                                                                                                  	|
| libjwt                                    	| MPL-2.0 License                                                             	| 1.13.0                                          	| JWT C Library                                                                                                                                                	|
| apparmor                                  	| GNU General Public License                                                  	| 3.0.3                                           	| Controls access based on paths of the program files                                                                                                          	|
| nsfcac/grafana-plugin                     	| Apache-2.0                                                                  	| 2.1.0                                           	| Machine Learning Framework                                                                                                                                   	|
| apparmor                                  	| GNU General Public License                                                  	| 3.0.3                                           	| Controls access based on paths of the program files                                                                                                          	|
| snoopy                                    	| GPL 2.0                                                                     	| 2.4.15                                          	| Snoopy is a small library that logs all program executions on your   Linux/BSD system                                                                        	|


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
	

# [Frequently asked questions](FAQ.md)

# Limitations
* Removal of Slurm and Kubernetes component roles are not supported. However, skip tags can be provided at the start of installation to select the component roles.​  
* After installing the Omnia control plane, changing the manager node is not supported. If you need to change the manager node, you must redeploy the entire cluster.  
* Dell Technologies provides support to the Dell-developed modules of Omnia. All the other third-party tools deployed by Omnia are outside the support scope.​
* To change the Kubernetes single node cluster to a multi-node cluster or change a multi-node cluster to a single node cluster, you must either redeploy the entire cluster or run `kubeadm reset -f` on all the nodes of the cluster. You then need to run the *omnia.yml* file and skip the installation of Slurm using the skip tags.  
* In a single node cluster, the login node and Slurm functionalities are not applicable. However, Omnia installs FreeIPA Server and Slurm on the single node.  
* To change the Kubernetes version from 1.16 to 1.19 or 1.19 to 1.16, you must redeploy the entire cluster.  
* The Kubernetes pods will not be able to access the Internet or start when firewalld is enabled on the node. This is a limitation in Kubernetes. So, the firewalld daemon will be disabled on all the nodes as part of omnia.yml execution.
* Only one storage instance (Powervault) is currently supported in the HPC cluster.
* Cobbler web support has been discontinued from Omnia 1.2 onwards.


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
