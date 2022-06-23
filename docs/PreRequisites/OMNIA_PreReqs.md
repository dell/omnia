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

>> **Note**:
>>	* The Hostname should not contain the following characters: , (comma), \. (period) or _ (underscore). However, the **domain name** is allowed commas and periods.
>>	* The Hostname cannot start or end with a hyphen (-).
>>	* No upper case characters are allowed in the hostname.
>>	* The hostname cannot start with a number.

## NFS bolt-on
* Ensure that an existing NFS server is running. NFS clients are mounted using the existing NFS server's IP.
* Fill out the `nfs_bolt_on` variable in the `omnia_config.yml` file in JSON format using the samples provided [here](../Input_Parameter_Guide/omnia_config.md)
* This role runs on manager, compute and login nodes.
* There are 3 ways to configure the feature:
  1. **Single NFS node** : A single NFS filesystem is mounted from a single NFS server. The value of `nfs_bolt_on` would be <br> `- { server_ip: xx.xx.xx.xx, server_share_path: "/mnt/share", client_share_path: "/mnt/client", client_mount_options: "nosuid,rw,sync,hard,intr  " }`
  2. **Multiple Mount NFS Filesystem**: Multiple filesystems are mounted from a single NFS server. The value of `nfs_bolt_on` would be <br>` - { server_ip: xx.xx.xx.xx, server_share_path: "/mnt/server1", client_share_path: "/mnt/client1", client_mount_options: "nosuid,rw,sync,hard,intr" }` <br> `- { server_ip: xx.xx.xx.xx, server_share_path: "/mnt/server2", client_share_path: "/mnt/client2", client_mount_options: "nosuid,rw,sync,hard,intr  " }`
  3. **Multiple NFS Filesystems**: Multiple filesystems are mounted from multiple NFS servers. The value of `nfs_bolt_on` would be <br> ` - { server_ip: xx.xx.xx.xx, server_share_path: "/mnt/server1", client_share_path: "/mnt/client1", client_mount_options: "nosuid,rw,sync,hard,intr" }` <br> `- { server_ip: yy.yy.yy.yy, server_share_path: "/mnt/server2", client_share_path: "/mnt/client2", client_mount_options: "nosuid,rw,sync,hard,intr  " }` <br> `- { server_ip: zz.zz.zz.zz, server_share_path: "/mnt/server3", client_share_path: "/mnt/client3", client_mount_options: "nosuid,rw,sync,hard,intr  " } `
Omnia supports all NFS mount options. For a list of mount options, [click here](https://linux.die.net/man/5/nfs).