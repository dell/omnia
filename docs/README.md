**Omnia** (Latin: all or everything) is a deployment tool to configure Dell EMC PowerEdge servers running standard RPM-based Linux OS images into clusters capable of supporting HPC, AI, and data analytics workloads. It uses Slurm, Kubernetes, and other packages to manage jobs and run diverse workloads on the same converged solution. It is a collection of [Ansible](https://ansible.org) playbooks, is open source, and is constantly being extended to enable comprehensive workloads.

## Blogs about Omnia
- [Introduction to Omnia](https://infohub.delltechnologies.com/p/omnia-open-source-deployment-of-high-performance-clusters-to-run-simulation-ai-and-data-analytics-workloads/)
- [Taming the Accelerator Cambrian Explosion with Omnia](https://infohub.delltechnologies.com/p/taming-the-accelerator-cambrian-explosion-with-omnia/)
- [Containerized HPC Workloads Made Easy with Omnia and Singularity](https://infohub.delltechnologies.com/p/containerized-hpc-workloads-made-easy-with-omnia-and-singularity/)

## What Omnia does
Omnia can build clusters which use Slurm or Kubernetes (or both!) for workload management. Omnia will install software from a variety of sources, including:
- Standard CentOS and [ELRepo](http://elrepo.org) repositories
- Helm repositories
- Source code compilation
- [OpenHPC](https://openhpc.community) repositories (_coming soon!_)
- [OperatorHub](https://operatorhub.io) (_coming soon!_)

Whenever possible, Omnia will leverage existing projects rather than reinvent the wheel.

![Omnia draws from existing repositories](images/omnia-overview.png)

### Omnia stacks
Omnia can install Kubernetes or Slurm (or both), along with additional drivers, services, libraries, and user applications.
![Omnia Kubernetes Stack](images/omnia-k8s.png)

![Omnia Slurm Stack](images/omnia-slurm.png) 

## Deploying clusters using the Omnia Appliance
The Omnia Appliance will automate the entire cluster deployment process, starting with provisioning the operating system to servers.

Ensure all the prerequisites listed in [preparation to install Omnia Appliance](PREINSTALL_OMNIA_APPLIANCE.md) are met before installing the Omnia appliance.

For detailed instructions on installing the Omnia appliance, see [Install Omnia Appliance](INSTALL_OMNIA_APPLIANCE.md).

## Installing Omnia to servers with a pre-provisioned OS
Omnia can be deploy clusters to servers that already have an RPM-based Linux OS running on them, and are all connected to the Internet. Currently all Omnia testing is done on [CentOS](https://centos.org). Please see [Preparation to install Omnia](PREINSTALL_OMNIA.md) for instructions on network setup.

Once servers have functioning OS and networking, you can use Omnia to install and start Slurm and/or Kubernetes. Please see [Install Omnia using CLI](INSTALL_OMNIA.md) for detailed instructions.  

# System requirements  
Ensure the supported version of all the software are installed as per the following table and other versions than those listed are not supported by Omnia. This is to ensure that there is no impact to the functionality of Omnia.

Software and hardware requirements  |   Version
----------------------------------  |   -------
OS installed on the management node  |  CentOS 7.9 2009
OS deployed by Omnia on bare-metal servers | CentOS 7.9 2009 Minimal Edition
Cobbler  |  2.8.5
Ansible AWX  |  15.0.0
Slurm Workload Manager  |  20.11.7
Kubernetes Controllers  |  1.16.7
Kubeflow  |  1
Prometheus  |  2.23.0
Supported PowerEdge servers  |  R640, R740, R7525, C4140, DSS8440, and C6420

## Software managed by Omnia
Ensure the supported version of all the software are installed as per the following table and other versions than those listed are not supported by Omnia. This is to ensure that there is no impact to the functionality of Omnia.

Software	|	Licence	|	Compatible Version	|	Description
-----------	|	-------	|	----------------	|	-----------------
MariaDB	|	GPL 2.0	|	5.5.68	|	Relational database used by Slurm
Slurm	|	GNU General Public	|	20.11.7	|	HPC Workload Manager
Docker CE	|	Apache-2.0	|	20.10.2	|	Docker Service
NVIDIA container runtime	|	Apache-2.0	|	3.4.2	|	Nvidia container runtime library
Python PIP	|	MIT Licence	|	3.2.1	|	Python Package
Python2	|	-	|	2.7.5	|	-
Kubelet	|	Apache-2.0	|	1.16.7	|	Provides external, versioned ComponentConfig API types for configuring the kubelet
Kubeadm	|	Apache-2.0	|	1.16.7	|	"fast paths" for creating Kubernetes clusters
Kubectl	|	Apache-2.0	|	1.16.7	|	Command line tool for Kubernetes
JupyterHub	|	Modified BSD Licence	|	1.1.0	|	Multi-user hub
Kfctl	|	Apache-2.0	|	1.0.2	|	CLI for deploying and managing Kubeflow
Kubeflow	|	Apache-2.0	|	1	|	Cloud Native platform for machine learning
Helm	|	Apache-2.0	|	3.5.0	|	Kubernetes Package Manager
Helm Chart	|	-	|	0.9.0	|	-
TensorFlow	|	Apache-2.0	|	2.1.0	|	Machine Learning framework
Horovod	|	Apache-2.0	|	0.21.1	|	Distributed deep learning training framework for Tensorflow
MPI	|	Copyright (c) 2018-2019 Triad National Security,LLC. All rights reserved.	|	0.2.3	|	HPC library
CoreDNS	|	Apache-2.0	|	1.6.2	|	DNS server that chains plugins
CNI	|	Apache-2.0	|	0.3.1	|	Networking for Linux containers
AWX	|	Apache-2.0	|	15.0.0	|	Web-based User Interface
PostgreSQL	|	Copyright (c) 1996-2020, PostgreSQL Global Development Group	|	10.15	|	Database Management System
Redis	|	BSD-3-Clause Licence	|	6.0.10	|	In-memory database
NGINX	|	BSD-2-Clause Licence	|	1.14	|	-

# Known issue  
Issue: Hosts do not display on the AWX UI.  
	
Resolution:  
* Verify if `provisioned_hosts.yml` is present in the `omnia/appliance/roles/inventory/files` folder.
* Verify if hosts are not listed in the `provisioned_hosts.yml` file. If hosts are not listed, then servers are not PXE booted yet.
* If hosts are listed in the `provisioned_hosts.yml` file, then an IP address has been assigned to them by DHCP. However, hosts are not displayed on the AWX UI as the PXE boot is still in process or is not initiated.
* Check for the reachable and unreachable hosts using the `provisioned_report.yml` tool present in the `omnia/appliance/tools` folder. To run provisioned_report.yml, in the omnia/appliance directory, run `playbook -i roles/inventory/files/provisioned_hosts.yml tools/provisioned_report.yml`.

# [Frequently asked questions](FAQ.md)

# Limitations
1. Removal of Slurm and Kubernetes component roles are not supported. However, skip tags can be provided at the start of installation to select the component roles.​
2. After the installation of the Omnia appliance, changing the manager node is not supported. If you need to change the manager node, you must redeploy the entire cluster.  
3. Dell Technologies provides support to the Dell developed modules of Omnia. All the other third-party tools deployed by Omnia are outside the support scope.​
4. To change the Kubernetes single node cluster to a multi-node cluster or to change a multi-node cluster to a single node cluster, you must either redeploy the entire cluster or run `kubeadm reset -f` on all the nodes of the cluster. You then need to run `omnia.yml` file and skip the installation of Slurm using the skip tags.
# Contributing to Omnia
The Omnia project was started to give members of the [Dell Technologies HPC Community](https://dellhpc.org) a way to easily setup clusters of Dell EMC servers, and to contribute useful tools, fixes, and functionality back to the HPC Community.

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
