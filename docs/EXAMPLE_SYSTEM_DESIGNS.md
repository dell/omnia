## Example System Designs
Omnia can configure systems which use Ethernet or Infiniband-based fabric to connect the compute servers.

![Example system configuration with Ethernet fabric](images/example-system-ethernet.png)

![Example system configuration with Infiniband fabric](images/example-system-infiniband.png)

## Internet Access
Since Omnia 1.2, only the control plane requires internet access. In such a situation, the network topology would follow the below diagram:
![Network Connections when only the Control Plane is connected to Internet](images/Omnia_NetworkConfig_NoInet.png)

If the user would like to have all compute nodes connect to the internet, the following network diagram can be followed.
![Network Connections when all servers are connected to the internet](images/Omnia_NetworkConfig_Inet.png)

