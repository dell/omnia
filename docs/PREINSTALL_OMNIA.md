# Preparation to install Omnia

## Assumptions
Ensure that the following prerequisites are met:
* The manager and compute nodes must be running CentOS 7.9 2009 OS.
* All nodes are connected to the network and have access to Internet.
* SSH Keys for root have been installed on all nodes to allow for password-less SSH.
* On the manager node, install Ansible and Git using the following commands:
	* `yum install epel-release -y`
	* `yum install ansible-2.9.18 git -y`  
__Note:__ Ansible must be installed using __yum__. If Ansible is installed using __pip3__, re-install it using the __yum__ command again.


## Example system designs
Omnia can configure systems which use Ethernet or Infiniband-based fabric to connect the compute servers.

![Example system configuration with Ethernet fabric](images/example-system-ethernet.png)

![Example system configuration with Infiniband fabric](images/example-system-infiniband.png)

## Network Setup
Omnia assumes that servers are already connected to the network and have access to the internet.
### Network Topology
Possible network configurations include:
* A flat topology where all nodes are connected to a switch which includes an uplink to the internet. This requires multiple externally-facing IP addresses
* A hierarchical topology where compute nodes are connected to a common switch, but the manager node contains a second network connection which is connected to the internet. All outbound/inbound traffic would be routed through the manager node. This requires setting up firewall rules for IP masquerade, see [here](https://www.server-world.info/en/note?os=CentOS_7&p=firewalld&f=2) for an example.
### IP and Hostname Assignment
The recommended setup is to assign IP addresses to individual servers. This can be done manually by logging onto each node, or via DHCP.
