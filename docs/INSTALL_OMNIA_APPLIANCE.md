# Install the Omnia appliance

## Prerequisites
* Ensure that all the prerequisites listed in the [Prerequisites to install the Omnia appliance](PREINSTALL_OMNIA_APPLIANCE.md) file are met before installing the Omnia appliance.
* After the installation of the Omnia appliance, changing the manager node is not supported. If you need to change the manager node, you must redeploy the entire cluster.  
* You must have root privileges to perform installations and configurations using the Omnia appliance.
* If there are errors when any of the following Ansible playbook commands are run, re-run the commands again.

## Steps to install the Omnia appliance

1. On the management node, change the working directory to the directory where you want to clone the Omnia Git repository.
2. Clone the Omnia repository:
``` 
git clone -b release https://github.com/dellhpc/omnia.git 
```
3. Change the directory to __omnia__: `cd omnia`
4. Edit the `omnia_config.yml` file to:
* Provide passwords for mariaDB Database (for Slurm accounting), Kubernetes Pod Network CIDR, Kubernetes CNI under `mariadb_password` and `k8s_cni` respectively.  
__Note:__ 
* Supported values for Kubernetes CNI are calico and flannel. The default value of CNI considered by Omnia is calico.	
* The default value of Kubernetes Pod Network CIDR is 10.244.0.0/16. If 10.244.0.0/16 is already in use within your network, select a different Pod Network CIDR. For more information, see __https://docs.projectcalico.org/getting-started/kubernetes/quickstart__.

5. Change the directory to __omnia__->__appliance__: `cd omnia/appliance`
6. Edit the `appliance_config.yml` file to:  
	a. Provide passwords for Cobbler and AWX under `provision_password` and `awx_password` respectively.  
	__Note:__ Minimum length of the password must be at least eight characters and a maximum of 30 characters. Do not use these characters while entering a password: -, \\, "", and \'  
	
	b. Change the NIC for the DHCP server under `hpc_nic`, and the NIC used to connect to the Internet under `public_nic`. The default values of **hpc_nic** and **public_nic** are set to em1 and em2 respectively.  
	
	c. Provide the CentOS-7-x86_64-Minimal-2009 ISO file path under `iso_file_path`. This ISO file is used by Cobbler to provision the OS on the compute nodes.  
	__Note:__ It is recommended that the ISO image file is not renamed. And, you **must not** change the path of this ISO image file as the provisioning of the OS on the compute nodes may be impacted.
	
	d. Provide a mapping file for DHCP configuration under `mapping_file_path`. The **mapping_file.csv** template file is present under `omnia/examples`. Enter the details in the order: `MAC, Hostname, IP`. The header in the template file must not be deleted before saving the file.  
	If you want to continue without providing a mapping file, leave the `mapping_file_path` value as blank.  
	__Note:__ Ensure that duplicate values are not provided for MAC, Hostname, and IP in the mapping file. The Hostname should not contain the following characters: , (comma), \. (period), and _ (underscore).
	
	e. Provide valid DHCP range for HPC cluster under the variables `dhcp_start_ip_range` and `dhcp_end_ip_range`. 
	
	f. **GMT** is the default configured time zone set during the provisioning of OS on compute nodes. To change the time zone, edit the `timezone` variable and enter a time zone. You can set the time zone to **EST**, **CET**, **MST**, **CST6CDT**, or **PST8PDT**. For a list of available time zones, see the `appliance/common/files/timezone.txt` file. 
	
Omnia considers the following usernames as default:  
* `cobbler` for Cobbler Server
* `admin` for AWX
* `slurm` for MariaDB

7. Run `ansible-playbook appliance.yml` to install the Omnia appliance.  

Omnia creates a log file which is available at: `/var/log/omnia.log`.

**Note**: If you want to view the Cobbler and AWX passwords provided in the **appliance_config.yml** file, run `ansible-vault view appliance_config.yml --vault-password-file .vault_key`.  

## Provision operating system on the target nodes 
Omnia role used: *provision*  
Ports used by Cobbler:  
* TCP ports: 80,443,69
* UDP ports: 69,4011

To create the Cobbler image, Omnia configures the following:
* Firewall settings.
* The kickstart file of Cobbler which will enable the UEFI PXE boot.

To access the Cobbler dashboard, enter `https://<IP>/cobbler_web` where `<IP>` is the Global IP address of the management node. For example, enter
`https://100.98.24.225/cobbler_web` to access the Cobbler dashboard.

__Note__: After the Cobbler Server provisions the operating system on the nodes, IP addresses and host names are assigned by the DHCP service.  
* If a mapping file is not provided, the hostname to the server is provided based on the following format: **computexxx-xxx** where "xxx-xxx" is the last two octets of Host IP address. For example, if the Host IP address is 172.17.0.11 then the assigned hostname by Omnia is compute0-11.  
* If a mapping file is provided, the hostnames follow the format provided in the mapping file.  

__Note__: If you want to add more nodes, append the new nodes in the existing mapping file. However, do not modify the previous nodes in the mapping file as it may impact the existing cluster.  

## Install and configure Ansible AWX 
Omnia role used: *web_ui*  
The port used by AWX is __8081__.  
The AWX repository is cloned from the GitHub path: https://github.com/ansible/awx.git 

Omnia performs the following configurations on AWX:
* The default organization name is set to **Dell EMC**.
* The default project name is set to **omnia**.
* The credentials are stored in the **omnia_credential**.
* Two groups, namely compute and manager groups, are provided under **omnia_inventory**. You can add hosts to these groups using the AWX UI. 
* Pre-defined templates are provided: **DeployOmnia** and **DynamicInventory**
* **DynamicInventorySchedule** which is scheduled to run every 10 minutes updates the inventory details dynamically. 

To access the AWX dashboard, enter `http://<IP>:8081` where **\<IP>** is the Global IP address of the management node. For example, enter `http://100.98.24.225:8081` to access the AWX dashboard.

**Note**: The AWX configurations are automatically performed Omnia and Dell Technologies recommends that you do not change the default configurations provided by Omnia as the functionality may be impacted.

__Note__: Although AWX UI is accessible, hosts will be shown only after few nodes have been provisioned by Cobbler. It takes approximately 10 to 15 minutes to display the host details after the provisioning by Cobbler. If a server is provisioned but you are unable to view the host details on the AWX UI, then you can run the following command from __omnia__ -> __appliance__ ->__tools__ folder to view the hosts which are reachable.
```
ansible-playbook -i ../roles/inventory/provisioned_hosts.yml provision_report.yml
```

## Install Kubernetes and Slurm using AWX UI
Kubernetes and Slurm are installed by deploying the **DeployOmnia** template on the AWX dashboard.

1. On the AWX dashboard, under __RESOURCES__ __->__ __Inventories__, select **omnia_inventory**.
2. Select __GROUPS__, and then select either __compute__ or __manager__ group.
3. Select the __HOSTS__ tab.
4. To add the hosts provisioned by Cobbler, click **+**, and then select **Existing Host**. 
5. Select the hosts from the list and click __SAVE__.
6. To deploy Omnia, under __RESOURCES__ -> __Templates__, select __DeployOmnia__, and then click __LAUNCH__.
7. By default, no skip tags are selected and both Kubernetes and Slurm will be deployed. 
8. To install only Kubernetes, enter `slurm` and select **slurm**. 
9. To install only Slurm, select and add `kubernetes` skip tag. 

__Note:__
*	If you would like to skip the NFS client setup, enter `nfs_client` in the skip tag section to skip the **k8s_nfs_client_setup** role of Kubernetes.

10. Click **NEXT**.
11. Review the details in the **PREVIEW** window, and click **LAUNCH** to run the DeployOmnia template. 

__Note:__ If you want to install __JupyterHub__ and __Kubeflow__ playbooks, you have to first install the __JupyterHub__ playbook and then install the __Kubeflow__ playbook.

__Note:__ To install __JupyterHub__ and __Kubeflow__ playbooks:
*	From AWX UI, under __RESOURCES__ -> __Templates__, select __DeployOmnia__ template.
*	From __PLAYBOOK__ dropdown menu, select __platforms/jupyterhub.yml__ and launch the template to install JupyterHub playbook.
*	From __PLAYBOOK__ dropdown menu, select __platforms/kubeflow.yml__ and launch the template to install Kubeflow playbook.

__Note:__ When the Internet connectivity is unstable or slow, it may take more time to pull the images to create the Kubeflow containers. If the time limit is exceeded, the **Apply Kubeflow configurations** task may fail. To resolve this issue, you must redeploy Kubernetes cluster and reinstall Kubeflow by completing the following steps:
* Complete the PXE booting of the manager and compute nodes.
* In the `omnia_config.yml` file, change the k8s_cni variable value from calico to flannel.
* Run the Kubernetes and Kubeflow playbooks.

The DeployOmnia template may not run successfully if:
- The Manager group contains more than one host.
- The Compute group does not contain a host. Ensure that the Compute group is assigned with at least one host node.
- Under Skip Tags, when both kubernetes and slurm tags are selected.

After **DeployOmnia** template is run from the AWX UI, the **omnia.yml** file installs Kubernetes and Slurm, or either Kubernetes or slurm, as per the selection in the template on the management node. Additionally, appropriate roles are assigned to the compute and manager groups.

## Kubernetes roles

The following __kubernetes__ roles are provided by Omnia when __omnia.yml__ file is run:
- __common__ role:
	- Install common packages on manager and compute nodes
	- Docker is installed
	- Deploy time ntp/chrony
	- Install Nvidia drivers and software components
- **k8s_common** role: 
	- Required Kubernetes packages are installed
	- Starts the docker and Kubernetes services.
- **k8s_manager** role: 
	- __helm__ package for Kubernetes is installed.
- **k8s_firewalld** role: This role is used to enable the required ports to be used by Kubernetes. 
	- For __head-node-ports__: 6443, 2379-2380,10251,10250,10252
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

__Note:__ 
* After Kubernetes is installed and configured, few Kubernetes and calico/flannel related ports are opened in the manager and compute nodes. This is required for Kubernetes Pod-to-Pod and Pod-to-Service communications. Calico/flannel provides a full networking stack for Kubernetes pods.
* If Kubernetes Pods are unable to communicate with the servers when the DNS servers are not responding, then the Kubernetes Pod Network CIDR may be overlapping with the host network which is DNS issue. To resolve this issue:
1. In your Kubernetes cluster, run `kubeadm reset -f` on the nodes.
2. In the management node, edit the `omnia_config.yml` file to change the Kubernetes Pod Network CIDR. Suggested IP range is 192.168.0.0/16 and ensure you provide an IP which is not in use in your host network.
3. Execute omnia.yml and skip slurm using --skip-tags slurm
 
## Slurm roles

The following __Slurm__ roles are provided by Omnia when __omnia.yml__ file is run:
- **slurm_common** role:
	- Installs the common packages on manager node and compute node.
- **slurm_manager** role:
	- Installs the packages only related to manager node
	- This role also enables the required ports to be used by Slurm.  
	    **tcp_ports**: 6817,6818,6819  
		**udp_ports**: 6817,6818,6819
	- Creating and updating the Slurm configuration files based on the manager node requirements.
- **slurm_workers** role:
	- Installs the Slurm packages into all compute nodes as per the compute node requirements.
- **slurm_start_services** role: 
	- Starting the Slurm services so that communicates with manager node.
- **slurm_exporter** role: 
	- Slurm exporter is a package for exporting metrics collected from Slurm resource scheduling system to prometheus.
	- Slurm exporter is installed on the host like Slurm, and Slurm exporter will be successfully installed only if Slurm is installed.

## Add a new compute node to the cluster

If a new node is provisioned through Cobbler, the node address is automatically displayed on the AWX dashboard. The node is not assigned to any group. You can add the node to the compute group along with the existing nodes and run `omnia.yml` to add the new node to the cluster and update the configurations in the manager node.
