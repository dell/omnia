# Install Omnia

## Prerequisties
Perform the following tasks before installing Omnia:
* On the management node, install Ansible and Git using the following commands:
	* `yum install epel-release -y`
	* `yum install ansible git -y`

__Note:__ ansible should be installed using __yum__ only.

__Note:__ If ansible is installed using __pip3__, install it again using __yum__ only.

* Ensure a stable Internet connection is available on management node and target nodes. 
* CentOS 7.9 2009 is installed on the management node.
* To provision the bare metal servers,
	* Go to http://isoredirect.centos.org/centos/7/isos/x86_64/ and download the **CentOS-7-x86_64-Minimal-2009** ISO file to the following directory on the management node: `omnia/appliance/roles/provision/files`.
	* Rename the downloaded ISO file to `CentOS-7-x86_64-Minimal-2009.iso`.
* For DHCP configuration, you can provide a mapping file named mapping_file.csv under __omnia/appliance/roles/provision/files__. The details provided in the CSV file must be in the format: MAC, Hostname, IP __xx:xx:4B:C4:xx:44,validation01,172.17.0.81 xx:xx:4B:C5:xx:52,validation02,172.17.0.82__
__Note:__ Duplicate hostnames must not be provided in the mapping file and the hostname should not contain these characters: "_" and "."
* Connect one of the Ethernet cards on the management node to the HPC switch and one of the ethernet card connected to the __global_network__.
* If SELinux is not disabled on the management node, disable it from /etc/sysconfig/selinux and restart the management node.
* The default mode of PXE is __UEFI__ and the __BIOS legacy__ mode is not supported.
* The default boot order for the bare metal server should be __PXE__.
* Configuration of __RAID__ is not part of omnia. If bare metal server has __RAID__ controller installed then it's compulsory to create __VIRTUAL DISK__.

## Steps to install Omnia
1. On the management node, change the working directory to the directory where you want to clone the Omnia Git repository.
2. Clone the Omnia repository.
``` 
$ git clone https://github.com/dellhpc/omnia.git 
```
__Note:__ After the Omnia repository is cloned, a folder named __omnia__ is created. It is recommended that you do not rename this folder.

3. Change the directory to `omnia/appliance`
4. To provide passwords for Cobbler and AWX, edit the __`appliance_config.yml`__ file.
* If user want to provide the mapping file for DHCP configuration, go to  __appliance_config.yml__ file there is variable name __mapping_file_exits__ set as __true__ otherwise __false__.

Omnia considers the following usernames as default:  
* `cobbler` for Cobbler Server
* `admin` for AWX`
* `slurm` for Slurm

**Note**: 
* Minimum length of the password must be at least eight characters and maximum of 30 characters.
* Do not use these characters while entering a password: -, \\, "", and \'

5. Using the `appliance_config.yml` file, you can also change the NIC for the DHCP server under *hpc_nic* and the NIC used to connect to the Internet under public_nic. Default values of both __hpc_nic__ and __public_nic__ is set to em1 and em2 respectively.
6. The valid DHCP range for HPC cluster is set into two variables name __Dhcp_start_ip_range__ and __Dhcp_end_ip_range__ present in the __appliance_config.yml__ file.
7. To provide password for Slurm Database and Kubernetes CNI, edit the __`omnia_config.yml`__ file.

**Note**:
* Supported Kubernetes CNI : calico and flannel, default is __calico__.

To view the set passwords of __`appliance_config.yml`__ at a later time, run the following command under omnia->appliance:
```
ansible-vault view appliance_config.yml --vault-password-file .vault_key
```

To view the set passwords of __`omnia_config.yml`__ at a later time, run the following command:
```
ansible-vault view omnia_config.yml --vault-password-file .omnia_vault_key
```

  
5. To install Omnia, run the following command:
```
ansible-playbook appliance.yml -e "ansible_python_interpreter=/usr/bin/python2"
```
   
Omnia creates a log file which is available at: `/var/log/omnia.log`.

**Provision operating system on the target nodes**  
Omnia role used: *provision*

To create the Cobbler image, Omnia configures the following:
* Firewall settings are configured.
* The kickstart file of Cobbler will enable the UEFI PXE boot.

To access the Cobbler dashboard, enter `https://<IP>/cobbler_web` where `<IP>` is the Global IP address of the management node.  	For example, enter
`https://100.98.24.225/cobbler_web` to access the Cobbler dashboard.

__Note__: If a mapping file is not provided, the hostname to the server is given on the basis of following format: __compute<xxx>-<xxx>__ where "xxx" is the last 2 octets of Host Ip address
After the Cobbler Server provisions the operating system on the nodes, IP addresses and host names are assigned by the DHCP service. The host names are assigned based on the following format: **compute\<xxx>-xxx** where **xxx** is the Host ID (last 2 octet) of the Host IP address. For example, if the Host IP address is 172.17.0.11 then assigned hostname will be compute0-11.
__Note__: If a mapping file is provided, the hostnames follow the format provided in the mapping file.

**Install and configure Ansible AWX**  
Omnia role used: *web_ui*  
AWX repository is cloned from the GitHub path: https://github.com/ansible/awx.git 


Omnia performs the following configuration on AWX:
* The default organization name is set to **Dell EMC**.
* The default project name is set to **omnia**.
* Credential: omnia_credential
* Inventory: omnia_inventory with compute and manager groups
* Template: DeployOmnia and Dynamic Inventory
* Schedules: DynamicInventorySchedule which is scheduled for every 10 mins

To access the AWX dashboard, enter `http://<IP>:8081` where **\<IP>** is the Global IP address of the management node. For example, enter `http://100.98.24.225:8081` to access the AWX dashboard.

***Note**: The AWX configurations are automatically performed Omnia and Dell Technologies recommends that you do not change the default configurations provided by Omnia as the functionality may be impacted.

__Note__: Although AWX UI is accessible, hosts will be shown only after few nodes have been provisioned by a cobbler. It will take approx 10-15 mins. If any server is provisioned but user is not able to see any host on the AWX UI, then user can run __provision_report.yml__ playbook from __omnia__ -> __appliance__ ->__tools__ folder to see which hosts are reachable.


## Install Kubernetes and Slurm using AWX UI
Kubernetes and Slurm are installed by deploying the **DeployOmnia** template on the AWX dashboard.

1. On the AWX dashboard, under __RESOURCES__ __->__ __Inventories__, select __Groups__.
2. Select either __compute__ or __manager__ group.
3. Select the __Hosts__ tab.
4. To add the hosts provisioned by Cobbler, select __Add__ __->__ __Add__ __existing__ __host__, and then select the hosts from the list and click __Save__.
5. To deploy Omnia, under __RESOURCES__ -> __Templates__, select __DeployOmnia__ and click __LAUNCH__.
6. By default, no skip tags are selected and both Kubernetes and Slurm will be deployed. To install only Kubernetes, enter `slurm` and select **Create "slurm"**. Similarly, to install only Slurm, select and add `kubernetes` skip tag. 

__Note:__
*	If you would like to skip the NFS client setup, enter _nfs_client in the skip tag section to skip the k8s_nfs_client_setup__ role of Kubernetes.

7. Click **Next**.
8. Review the details in the **Preview** window, and click **Launch** to run the DeployOmnia template. 

To establish the passwordless communication between compute nodes and manager node:
1. In AWX UI, under __RESOURCES__ -> __Templates__, select __DeployOmnia__ template.
2. From __Playbook dropdown__ menu, select __appliance/tools/passwordless_ssh.yml__ and __Launch__ the template.

__Note:__ If you want to install __jupyterhub__ and __kubeflow__ playbooks, you have to first install the __jupyterhub__ playbook and then install the __kubeflow__ playbook.

__Note:__ To install __jupyterhub__ and __kubeflow__ playbook:
*	From __AWX UI__, under __RESOURCES__ -> __Templates__, select __DeployOmnia__ template.
*	From __Playbook dropdown__ menu, select __platforms/jupyterhub.yml__ option and __Launch__ the template to install jupyterhub playbook.
*	From __Playbook dropdown__ menu, select __platforms/kubeflow.yml__ option and __Launch__ the template to install kubeflow playbook.


The DeployOmnia template may not run successfully if:
- The Manager group contains more than one host.
- The Compute group does not contain a host. Ensure that the Compute group must be assigned with a minimum of one host node.
- Under Skip Tags, when both kubernetes and slurm tags are selected.

After **DeployOmnia** template is executed from the AWX UI, the **omnia.yml** file installs Kubernetes and Slurm, or either Kubernetes or slurm, as per the selection in the template on the management node. Additionally, appropriate roles are assigned to the compute and manager groups.

The following __kubernetes__ roles are provided by Omnia when __omnia.yml__ file is executed:
- __common__ role:
	- Install common packages on master and compute nodes
	- Docker is installed
	- Deploy time ntp/chrony
	- Install Nvidia drivers and software components
- __k8s_common__ role: 
	- Required Kubernetes packages are installed
	- Starts the docker and kubernetes services.
- __k8s_manager__ role: 
	- __helm__ package for Kubernetes is installed.
- __k8s_firewalld__ role: This role is used to enable the required ports to be used by Kubernetes. 
	- For __head-node-ports__: 6443, 2379-2380,10251,10252
	- For __compute-node-ports__: 10250,30000-32767
	- For __calico-udp-ports__: 4789
	- For __calico-tcp-ports__: 5473,179
	- For __flanel-udp-ports__: 8285,8472
- __k8s_nfs_server_setup__ role: 
	- A __nfs-share__ directory, __/home/k8nfs__, is created. Using this directory, compute nodes share the common files.
- __k8s_nfs_client_setup__ role
- __k8s_start_manager__ role: 
	- Runs the __/bin/kubeadm init__ command to initialize the Kubernetes services on manager node.
	- Initialize the Kubernetes services in the manager node and create service account for Kubernetes Dashboard
- __k8s_start_workers__ role: 
	- The compute nodes are initialized and joined to the Kubernetes cluster with the manager node. 
- __k8s_start_services__ role
	- Kubernetes services are deployed such as Kubernetes Dashboard, Prometheus, MetalLB and NFS client provisioner

__Note:__ Once kubernetes is installed and configured, few Kubernetes and calico/flannel related ports will be opened in the manager/compute nodes. This is required for kubernetes Pod-to-Pod and Pod-to-Service communications. Calico/flannel provides a full networking stack for kubernetes pods.

The following __Slurm__ roles are provided by Omnia when __omnia.yml__ file is executed:
- __slurm_common__ role:
	- Install the common packages on manager/head node and compute node.
- __slurm_manager__ role:
	- Install the packages only related to manager node
	- This role also enables the required ports to be used by slurm.
		__tcp_ports__: 6817,6818,6819
		__udp_ports__: 6817,6818,6819
	- Creating and updating the slurm configuration files based on the manager node requirements.
- __slurm_workers__ role:
	- Install the slurm packages into all compute nodes as per the compute node requirements.
- __slurm_start_services__ role: 
	- Starting the slurm services so that compute node starts to communicate with manager node.
- __slurm_exporter__ role: 
	- slurm exporter is a package for exporting metrics collected from slurm resource scheduling system to prometheus.
	- Slurm exporter is installed on the host just like slurm and slurm exporter will be successfully installed only if slurm is installed.