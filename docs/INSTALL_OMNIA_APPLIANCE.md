# Install the Omnia appliance

## Prerequisties
Ensure that all the prequisites listed in the [PREINSTALL_OMNIA_APPLIANCE](PREINSTALL_OMNIA_APPLIANCE.md) file are met before installing Omnia appliance

__Note:__ Changing the manager node after installation of Omnia is not supported by Omnia. If you want to change the manager node, you must redeploy the entire cluster.


## Steps to install the Omnia appliance
__Note:__ The user should have root privileges to perform installations and configurations using Omnia.
__Note:__ If there are errors when any of the following Ansible playbook commands are executed, re-run the commands again.  

1. Clone the Omnia repository.
``` 
$ git clone https://github.com/dellhpc/omnia.git 
```
__Note:__ After the Omnia repository is cloned, a folder named __omnia__ is created. It is recommended that you do not rename this folder.

2. Change the directory to `omnia/appliance`
3. To provide passwords for Cobbler and AWX, edit the __`appliance_config.yml`__ file.
* If user want to provide the mapping file for DHCP configuration, go to  __appliance_config.yml__ file there is variable name __mapping_file_exits__ set as __true__ otherwise __false__.

Omnia considers the following usernames as default:  
* `cobbler` for Cobbler Server
* `admin` for AWX
* `slurm` for MariaDB

**Note**: 
* Minimum length of the password must be at least eight characters and maximum of 30 characters.
* Do not use these characters while entering a password: -, \\, "", and \'

4. Using the `appliance_config.yml` file, you can also change the NIC for the DHCP server under *hpc_nic* and the NIC used to connect to the Internet under public_nic. Default values of both __hpc_nic__ and __public_nic__ is set to em1 and em2 respectively.
5. The valid DHCP range for HPC cluster is set into two variables name __Dhcp_start_ip_range__ and __Dhcp_end_ip_range__ present in the __appliance_config.yml__ file.
6. To provide password for mariaDB Database for Slurm accounting and Kubernetes CNI, edit the __`omnia_config.yml`__ file.

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

  
7. To install Omnia, run the following command:
```
ansible-playbook appliance.yml -e "ansible_python_interpreter=/usr/bin/python2"
```
   
Omnia creates a log file which is available at: `/var/log/omnia.log`.

**Provision operating system on the target nodes**  
Omnia role used: *provision*
Ports used by __Cobbler__
* __TCP__ ports: 80,443,69
* __UDP__ ports: 69,4011

To create the Cobbler image, Omnia configures the following:
* Firewall settings are configured.
* The kickstart file of Cobbler will enable the UEFI PXE boot.

To access the Cobbler dashboard, enter `https://<IP>/cobbler_web` where `<IP>` is the Global IP address of the management node. For example, enter
`https://100.98.24.225/cobbler_web` to access the Cobbler dashboard.

__Note__: If a mapping file is not provided, the hostname to the server is given on the basis of following format: __compute<xxx>-<xxx>__ where "xxx" is the last 2 octets of Host Ip address
After the Cobbler Server provisions the operating system on the nodes, IP addresses and host names are assigned by the DHCP service. The host names are assigned based on the following format: **compute\<xxx>-xxx** where **xxx** is the Host ID (last 2 octet) of the Host IP address. For example, if the Host IP address is 172.17.0.11 then assigned hostname will be compute0-11.
__Note__: If a mapping file is provided, the hostnames follow the format provided in the mapping file.

**Install and configure Ansible AWX**  
Omnia role used: *web_ui*
Port used by __AWX__ is __8081__.  
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

__Note:__ If you want to install __JupyterHub__ and __Kubeflow__ playbooks, you have to first install the __JupyterHub__ playbook and then install the __Kubeflow__ playbook.

__Note:__ To install __JupyterHub__ and __Kubeflow__ playbooks:
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
	- Install common packages on manager and compute nodes
	- Docker is installed
	- Deploy time ntp/chrony
	- Install Nvidia drivers and software components
- **k8s_common** role: 
	- Required Kubernetes packages are installed
	- Starts the docker and kubernetes services.
- **k8s_manager** role: 
	- __helm__ package for Kubernetes is installed.
- **k8s_firewalld** role: This role is used to enable the required ports to be used by Kubernetes. 
	- For __head-node-ports__: 6443, 2379-2380,10251,10252
	- For __compute-node-ports__: 10250,30000-32767
	- For __calico-udp-ports__: 4789
	- For __calico-tcp-ports__: 5473,179
	- For __flanel-udp-ports__: 8285,8472
- **k8s_nfs_server_setup** role: 
	- A __nfs-share__ directory, `/home/k8snfs`, is created. Using this directory, compute nodes share the common files.
- **k8s_nfs_client_setup** role
- **k8s_start_manager** role: 
	- Runs the __/bin/kubeadm init__ command to initialize the Kubernetes services on manager node.
	- Initialize the Kubernetes services in the manager node and create service account for Kubernetes Dashboard
- **k8s_start_workers** role: 
	- The compute nodes are initialized and joined to the Kubernetes cluster with the manager node. 
- **k8s_start_services** role
	- Kubernetes services are deployed such as Kubernetes Dashboard, Prometheus, MetalLB and NFS client provisioner

__Note:__ After Kubernetes is installed and configured, few Kubernetes and calico/flannel related ports will be opened in the manager and compute nodes. This is required for Kubernetes Pod-to-Pod and Pod-to-Service communications. Calico/flannel provides a full networking stack for Kubernetes pods.

The following __Slurm__ roles are provided by Omnia when __omnia.yml__ file is executed:
- **slurm_common** role:
	- Install the common packages on manager node and compute node.
- **slurm_manager** role:
	- Install the packages only related to manager node
	- This role also enables the required ports to be used by slurm.  
	    **tcp_ports**: 6817,6818,6819  
		**udp_ports**: 6817,6818,6819
	- Creating and updating the slurm configuration files based on the manager node requirements.
- **slurm_workers** role:
	- Install the slurm packages into all compute nodes as per the compute node requirements.
- **slurm_start_services** role: 
	- Starting the slurm services so that compute node starts to communicate with manager node.
- **slurm_exporter** role: 
	- slurm exporter is a package for exporting metrics collected from slurm resource scheduling system to prometheus.
	- Slurm exporter is installed on the host just like slurm and slurm exporter will be successfully installed only if slurm is installed.

## Adding a new compute node to the Cluster

If a new node is provisioned through Cobbler, the node address is automatically displayed in AWX UI. This node does not belong to any group. The user can add the node to the compute group and execute __omnia.yml__ to add the new node to the cluster and update the configurations in the manager node.
