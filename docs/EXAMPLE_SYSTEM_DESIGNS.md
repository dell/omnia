## Example system designs
Omnia can configure systems which use Ethernet or Infiniband-based fabric to connect the compute servers.

![Example system configuration with Ethernet fabric](images/example-system-ethernet.png)

![Example system configuration with Infiniband fabric](images/example-system-infiniband.png)

## Network Setup
With Omnia 1.2, only the control plane requires internet access. In such a situation, the network topology would follow the below diagram:
![Network Connections when only the Control Plane is connected to Internet](images/Omnia_NetworkConfig_NoInet.png)

If the user would like to have all compute nodes connect to the internet, the following network diagram can be followed.
![Network Connections when all servers are connected to the internet](images/Omnia_NetworkConfig_Inet.png)

### Network Topology
Possible network configurations include:
* A flat topology where all nodes are connected to a switch which includes an uplink to the internet. This requires multiple externally-facing IP addresses
* A hierarchical topology where compute nodes are connected to a common switch, but the manager node contains a second network connection which is connected to the internet. All outbound/inbound traffic would be routed through the manager node. This requires setting up firewall rules for IP masquerade, see [here](https://www.server-world.info/en/note?os=CentOS_7&p=firewalld&f=2) for an example.
