# Prerequisites before installing `omnia.yml`


## Installing BeeGFS Client
* If the user intends to use BeeGFS, ensure that a BeeGFS cluster has been set up with beegfs-mgmtd, beegfs-meta, beegfs-storage services running.
  Ensure that the following ports are open for TCP and UDP connectivity:

  | Port | Service                           |
  |------|-----------------------------------|
  | 8008 | Management service (beegfs-mgmtd) |
  | 8003 | Storage service (beegfs-storage)  |
  | 8004 | Client service (beegfs-client)    |
  | 8005 | Metadata service (beegfs-meta)    |
  | 8006 | Helper service (beegfs-helperd)   |

To open the ports required, use the following steps:
1. `firewall-cmd --permanent --zone=public --add-port=<port number>/tcp`
2. `firewall-cmd --permanent --zone=public --add-port=<port number>/udp`
3. `firewall-cmd --reload`
4. `systemctl status firewalld`

* Ensure that the nodes in the inventory have been assigned roles: manager, compute, login_node (optional), nfs_node

## Pre-requisites Before Enabling Security: Login Node

* Verify that the login node host name has been set. If not, use the following steps to set it.
    * Set hostname of the login node to hostname.domainname format using the below command:
      `hostnamectl set-hostname <hostname>.<domainname>`
  >>Eg: `hostnamectl set-hostname login-node.omnia.test`
    * Add the set hostname in `/etc/hosts` using vi editor.

  `vi /etc/hosts`

    * Add the IP of the login node with the above hostname using `hostnamectl` command in last line of the file.

  __Eg:__  xx.xx.xx.xx <hostname>

>> __Note:__
>>	* The Hostname should not contain the following characters: , (comma), \. (period) or _ (underscore). However, the **domain name** is allowed commas and periods.
>>	* The Hostname cannot start or end with a hyphen (-).
>>	* No upper case characters are allowed in the hostname.
>>	* The hostname cannot start with a number.
