# Pre-requisites Before Running Control Plane
* Ensure that a stable Internet connection is available on control plane.
* Rocky 8 or Red Hat 8.x is installed on the control plane.
* Ensure that the root partition (/) has a minimum of 50% (~35G) free space. 
* To provision the bare metal servers, download one of the following ISOs for deployment:
    1. [Leap 15.3](https://get.opensuse.org/leap/)
    2. [Rocky 8](https://rockylinux.org/)
    3. [Red Hat 8.x](https://www.redhat.com/en/enterprise-linux-8)
* As a best practice, ensure that PowerCap policy is disabled and the BIOS system profile is set to Performance on the Control Plane.
* For DHCP configuration, you can provide a host mapping file (Example available [here](../../examples/host_mapping_file_os_provisioning.csv)). If the mapping file is not provided and the variable is left blank, a default mapping file will be created. The provided details must be in the format: MAC address, Hostname, IP address, Component_role. For example, `10:11:12:13,server1,100.96.20.66,compute` and  `14:15:16:17,server2,100.96.22.199,manager` are valid entries.  
>> __Note:__  
>>  * In the `omnia/examples` folder, a **mapping_host_file.csv** template is provided which can be used for DHCP configuration. The header in the template file must not be deleted before saving the file. It is recommended to provide this optional file as it allows IP assignments provided by Omnia to be persistent across control plane reboots.  
>>	* The Hostname should not contain the following characters: , (comma), \. (period) or _ (underscore). However, the **domain name** is allowed commas and periods. 
>>	* The Hostname cannot start or end with a hyphen (-).
>>	* No upper case characters are allowed in the hostname.
>>	* The hostname cannot start with a number.
* Connect one of the Ethernet cards on the control plane to the HPC switch. The other Ethernet card must be connected to the internet network. 
* Ensure that all connection names under the network manager match their corresponding device names. This can be verified using the command `nmcli connection`. In the event of a mismatch, edit the file `/etc/sysconfig/network-scripts/ifcfg-<nic name>` using vi editor. 
  * You must have root privileges to perform installations and configurations using the Omnia control plane.
    * On the control plane, ensure that Python 3.6 and Ansible are installed (The following commands are compatible with all 3 OS's unless marked otherwise).  
        * Run the following commands to install Python 3.6:  
          `dnf install epel-release -y` <br><br> `dnf install python3 -y`
        * Run the following commands to install Ansible:
           ```
           pip3.6 install --upgrade pip
           python3.6 -m pip install ansible
           ```
        After the installation is complete, run `ansible --version` to verify if the installation is successful. In the output, ensure that the executable location path is present in the PATH variable by running `echo $PATH`.
        If executable location path is not present, update the path by running `export PATH=$PATH:<executable location>\`.  
	
        For example,  
        ```
        ansible -- version
        ansible 2.10.9
        config file = None
        configured module search path = ['/root/.ansible/plugins/modules', '/usr/share/ansible/plugins/modules']
        ansible python module location = /usr/local/lib/python3.6/site-packages/ansible
        executable location = /usr/local/bin/ansible
        python version = 3.6.8 (default, Aug 24 2020, 17:57:11) [GCC 8.3.1 20191121 (Red Hat 8.3.1-5)]
        ```
        The executable location is `/usr/local/bin/ansible`. Update the path by running the following command:
        ```
        export PATH=$PATH:/usr/local/bin
        ```  
	
    >>__Note__:
     >> * To deploy Omnia, Python 3.6 provides bindings to system tools such as RPM, DNF, and SELinux. As versions greater than 3.6 do not provide these bindings to system tools, ensure that you install Python 3.6 with dnf.  
     >> * If SELinux is not disabled on the control plane, disable it from `/etc/sysconfig/selinux` and restart the control plane.
     >> * If Ansible version 2.9 or later is installed, ensure it is uninstalled before installing a newer version of Ansible. Run the following commands to uninstall Ansible before upgrading to newer version.
    >> 1. `pip uninstall ansible`
    >> 2. `pip uninstall ansible-base (if ansible 2.9 is installed)`
    >> 3. `pip uninstall ansible-core` (if ansible 2.10 > version is installed)

* If Red Hat is in use on the control plane, ensure that RHEL subscription is enabled **before** running `control_plane.yml`. Not only does Omnia not enable RHEL subscription on the control plane, package installation may fail if RHEL subscription is disabled.
* Users should also ensure that all repos are available on Red Hat control planes.
* On the control plane, run the following commands to install Git: <br>
  `dnf install epel-release -y` (Only if Rocky is in use on the control plane) <br><br> `dnf install git -y`
* If the user intends to use BeeGFS, ensure that a BeeGFS cluster has been set up with beegfs-mgmtd, beegfs-meta, beegfs-storage services running on the control plane.
* Ensure that the following ports are open for TCP and UDP connectivity:
  | Port | Service                           |
  |------|-----------------------------------|
  | 8008 | Management service (beegfs-mgmtd) |
  | 8003 | Metadata service (beegfs-meta)    |
  | 8004 | Storage service (beegfs-storage)  |
  | 8005 | Client service (beegfs-client)    |

To open the ports required, use the following steps:
1. `firewall-cmd --permanent --zone=public --add-port=<port number>/tcp`
2. `firewall-cmd --permanent --zone=public --add-port=<port number>/udp`
3. `firewall-cmd --reload`
4. `systemctl status firewalld`

>> **Note**:
>> * After the installation of the Omnia appliance, changing the control plane is not supported. If you need to change the control plane, you must redeploy the entire cluster.
>> * If there are errors while executing any of the Ansible playbook commands, then re-run the commands.  

* Fill in all required parameters under `/control_plane/input_parameters` and security parameters under `omnia_security_config.yml`/ `security_vars.yml` based on the provided [Input Parameter Guide](../Input_Parameter_Guide)
