Releases
============
1.4.1
------

* R660, R6625 and C6620 platforms are now supported as control planes or target nodes.

* One touch provisioning now allows for OFED installation, NVIDIA   CUDA-toolkit installation along with iDRAC and InfiniBand IP configuration on   target nodes.

* Potential servers can now be discovered via iDRAC.

* Servers can be provisioned automatically without manual intervention for booting/PXE settings.

* Target node provisioning status can now be checked on the control plane by viewing the OmniaDB.

* Omnia clusters can be configured with passwordless SSH for seamless execution of HPC jobs run by non-root users.

* Accelerator drivers can be installed on Rocky target nodes in addition to RHEL.


1.4
----

* 	Provisioning of remote nodes through PXE boot by providing TOR switch IP

*	Provisioning of remote nodes through PXE boot by providing mapping file

*	PXE provisioning of remote nodes through admin NIC or shared LOM NIC

*	Database update of mac address, hostname and admin IP

*	Optional monitoring support(Grafana installation) on control plane

*	OFED installation on the remote nodes

*	CUDA installation on the remote nodes

*	AMD accelerator and ROCm support on the remote nodes

*	Omnia playbook execution with Kubernetes, Slurm & FreeIPA installation in all compute nodes

*	Infiniband switch configuration and split port functionality

*   Added support for Ethernet Z series switches.

1.3
-----

* CLI support for all Omnia playbooks (AWX GUI is now optional/deprecated).

* Automated discovery and configuration of all devices (including PowerVault, InfiniBand, and ethernet switches) in shared LOM configuration.

* Job based user access with Slurm.

* AMD server support (R6415, R7415, R7425, R6515, R6525, R7515, R7525, C6525).

* PowerVault ME5 series support (ME5012, ME5024, ME5084).

* PowerVault ME4 and ME5 SAS Controller configuration and NFS server, client configuration.

* NFS bolt-on support.

* BeeGFS bolt-on support.

* Lua and Lmod installation on manager and compute nodes running RedHat 8.x, Rocky 8.x and Leap 15.3.

* Automated setup of FreeIPA client on all nodes.

* Automate configuration of PXE device settings (active NIC) on iDRAC.

1.2.2
------
* Bugfix patch release to address AWX Inventory not being updated.

1.2.1
------

* HPC cluster formation using shared LOM network

* Supporting PXE boot on shared LOM network as well as high speed Ethernet or InfiniBand path.

* Support for BOSS Control Card

* Support for RHEL 8.x with ability to activate the subscription

* Ability to upgrade Kernel on RHEL

* Bolt-on Support for BeeGFS

1.2.0.1
---------

* Bugfix patch release which address the broken cobbler container issue.

* Rocky 8.6 Support

1.2
------

* Omnia supports Rocky 8.5 full OS on the Control Plane

* Omnia supports ansible version 2.12 (ansible-core) with python 3.6 support

* All packages required to enable the HPC/AI cluster are deployed as a pod on control plane

* Omnia now installs Grafana as a single pane of glass to view logs, metrics and telemetry visualization

* Compute node provisioning can be done via PXE and iDRAC

* Omnia supports multiple operating systems on the cluster including support for Rocky 8.5 and OpenSUSE Leap 15.3

* Omnia can deploy compute nodes with a single NIC.

* All Cluster metrics can be viewed using Grafana on the Control plane (as opposed to checking the manager node on each cluster)

* AWX node inventory now displays service tags with the relevant operating system.

* Omnia adheres to most of the requirements of NIST 800-53 and NIST 800-171 guidelines on the control plane and login node.

* Omnia has extended the FreeIPA feature to provide authentication and authorization on Rocky Nodes.

* Omnia uses [389ds}(https://directory.fedoraproject.org/) to provide authentication and authorization on Leap Nodes.

* Email Alerts have been added in case of login failures.

* Administrator can restrict users or hosts from accessing the control plane and login node over SSH.

* Malicious or unwanted network software access can be restricted by the administrator.

* Admins can restrict the idle time allowed in an ssh session.

* Omnia installs apparmor to restrict program access on leap nodes.

* Security on audit log access is provided.

* Program execution on the control plane and login node is logged using snoopy tool.

* User activity on the control plane and login node is monitored using psacct/acct tools installed by Omnia

* Omnia fetches key performance indicators from iDRACs present in the cluster

* Omnia also supports fetching performance indicators on the nodes in the cluster when SLURM jobs are running.

* The telemetry data is plotted on Grafana to provide better visualization capabilities.

* Four visualization plugins are supported to provide and analyze iDRAC and Slurm data.

        * Parallel Coordinate

        * Spiral

        * Sankey

        * Stream-net (aka. Power Map)

* In addition to the above features, changes have been made to enhance the performance of Omnia.
