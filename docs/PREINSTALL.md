# Pre-Installation Preparation

## Assumptions
Omnia assumes that prior to installation:
* Systems have a base operating system (currently CentOS 7 or 8)
* Network(s) has been cabled and nodes can reach the internet
* SSH Keys for `root` have been installed on all nodes to allow for password-less SSH
* Ansible is installed on the master node
```
yum install ansible
```

## Example system designs
Omnia can configure systems which use Ethernet- or Infiniband-based fabric to connect the compute servers.

![Example system configuration with Ethernet fabric](images/example-system-ethernet.png)

![Example system configuration with Infiniband fabric](images/example-system-infiniband.png)

## Network Setup
Omnia assumes that servers are already connected to the network and have access to the internet. Possible network configurations include:
* 
