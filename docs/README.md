**Omnia** (Latin: all or everything) is a deployment tool to configure Dell EMC PowerEdge servers running standard RPM-based Linux OS images into clusters capable of supporting HPC, AI, and data analytics workloads. It uses Slurm, Kubernetes, and other packages to manage jobs and run diverse workloads on the same converged solution. It is a collection of [Ansible](https://ansible.org) playbooks, is open source, and is constantly being extended to enable comprehensive workloads.

## What Omnia Does
Omnia can build clusters which use Slurm or Kubernetes (or both!) for workload management. Omnia will install software from a variety of sources, including:
- Standard CentOS and [ELRepo](http://elrepo.org) repositories
- Helm repositories
- Source code compilation
- [OpenHPC](https://openhpc.community) repositories (_coming soon!_)
- [OperatorHub](https://operatorhub.io) (_coming soon!_)

Whenever possible, Omnia will leverage existing projects rather than reinvent the wheel.

![Omnia draws from existing repositories](images/omnia-overview.png)

### Omnia Stacks
Omnia can install Kubernetes or Slurm (or both), along with additional drivers, services, libraries, and user applications.
![Omnia Kubernetes Stack](images/omnia-k8s.png)

![Omnia Slurm Stack](images/omnia-slurm.png) 

## Installing Omnia
Omnia requires that servers already have an RPM-based Linux OS running on them, and are all connected to the Internet. Currently all Omnia testing is done on [CentOS](https://centos.org). Please see [PREINSTALL_OMNIA](PREINSTALL_OMNIA.md) for instructions on network setup.

Once servers have functioning OS and networking, you can using Omnia to install and start Slurm and/or Kubernetes. Please see [INSTALL_OMNIA](INSTALL_OMNIA.md) for detailed instructions.

To install the Omnia appliance, see [PREINSTALL_OMNIA_APPLIANCE](PREINSTALL_OMNIA_APPLIANCE.md) and [INSTALL_OMNIA_APPLIANCE](INSTALL_OMNIA_APPLIANCE.md) files.

# Support Matrix

Software and hardware requirements  |   Version
----------------------------------  |   -------
OS installed on the management node  |  CentOS 7.9 2009
OS deployed by Omnia on bare-metal servers | CentOS 7.9 2009 Minimal Edition
Cobbler  |  2.8.5
Ansible AWX Version  |  15.0.0
Slurm Workload Manager  |  20.11.2
Kubernetes Controllers  |  1.16.7
Kubeflow  |  1
Prometheus  |  2.23.0
Supported PowerEdge servers  |  R640, R740, R7525, C4140, DSS8440, and C6420

__Note:__ For more information related to softwares, refer the __Software Supported__ section

## Software Supported
Software	|	Licence	|	Compatible Version	|	Description
-----------	|	-------	|	----------------	|	-----------------
MariaDB	|	GPL 2.0	|	5.5.68	|	Relational database used by Slurm
Slurm	|	GNU General Public	|	20.11.2	|	HPC Workload Manager
Docker CE	|	Apache-2.0	|	20.10.2	|	Docker Service
nvidia container runtime	|	Apache-2.0	|	3.4.0	|	Nvidia container runtime library
Python-pip	|	MIT Licence	|	3.2.1	|	Python Package
Python2	|	-	|	2.7.5	|	-
kubelet	|	Apache-2.0	|	1.16.7	|	Provides external, versioned ComponentConfig API types for configuring the kubelet
kubeadm	|	Apache-2.0	|	1.16.7	|	"fast paths" for creating Kubernetes clusters
kubectl	|	Apache-2.0	|	1.16.7	|	Command line tool for kubernetes
jupyterhub	|	Modified BSD Licence	|	1.1.0	|	Multi-user hub
kfctl	|	Apache-2.0	|	1.0.2	|	CLI for deploying and managing kubeflow
kubeflow	|	Apache-2.0	|	1	|	Cloud Native platform for machine learning
helm	|	Apache-2.0	|	3.5.0	|	Kubernetes Package Manager
helm chart	|	-	|	0.9.0	|	-
tensorflow	|	Apache-2.0	|	2.1.0	|	Machine Learning framework
horovod	|	Apache-2.0	|	0.21.1	|	Distributed deep learning training framework for Tensorflow
MPI	|	Copyright (c) 2018-2019 Triad National Security,LLC. All rights reserved.	|	0.2.3	|	HPC library
spark	|	Apache-2.0	|	2.4.7	|	Unified analytics engine for large scale data processing
coreDNS	|	Apache-2.0	|	1.6.7	|	DNS server that chains plugins
cni	|	Apache-2.0	|	0.3.1	|	Networking for Linux containers
awx	|	Apache-2.0	|	15.0.0 or latest	|	Web based user interface
postgreSQL	|	Copyright (c) 1996-2020, PostgreSQL Global Development Group	|	11	|	Database Management System
redis	|	BSD-3-Clause Licence	|	6.0.8	|	in-memory database
nginx	|	BSD-2-Clause Licence	|	1.17.0	|	-

### Contributing to Omnia
The Omnia project was started to give members of the [Dell Technologies HPC Community](https://dellhpc.org) a way to easily setup clusters of Dell EMC servers, and to contribute useful tools, fixes, and functionality back to the HPC Community.

#### Open to All
While we started Omnia within the Dell Technologies HPC Community, that doesn't mean that it's limited to Dell EMC servers, networking, and storage. This is an open project, and we want to encourage *everyone* to use and contribute to Omnia!

##### Anyone Can Contribute!
It's not just new features and bug fixes that can be contributed to the Omnia project! Anyone should feel comfortable contributing. We are asking for all types of contributions:
* New feature code
* Bug fixes
* Documentation updates
* Feature suggestions
* Feedback
* Validation that it works for your particular configuration

If you would like to contribute, see [CONTRIBUTING](https://github.com/dellhpc/omnia/blob/devel/CONTRIBUTING.md).

###### [Omnia Contributors](CONTRIBUTORS.md)
