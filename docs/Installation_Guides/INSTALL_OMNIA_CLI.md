# Install Omnia

The following sections provide details on installing `omnia.yml` using CLI.  

To install the Omnia control plane and manage workloads on your cluster using the Omnia control plane, see [Install the Omnia Control Plane](INSTALL_CONTROL_PLANE.md) and [Monitor Kubernetes and Slurm](../Monitoring/MONITOR_CLUSTERS.md) for more information.

## Steps to install Omnia using CLI

1. Clone the Omnia repository:
``` 
git clone https://github.com/dellhpc/omnia.git 
```  

<!---
From release branch: 
``` 
git clone -b release https://github.com/dellhpc/omnia.git 
```-->  

>> **Note**: After the Omnia repository is cloned, a folder named __omnia__ is created. Ensure that you do not rename this folder.

2. Change the directory to __omnia__: `cd omnia`

3. In the `omnia_config.yml` file, provide the required details (Check the [parameter guide](../Input_Parameter_Guide/omnia_config.md) for more information).
>> **Note**:  Without the login node, Slurm jobs can be scheduled only through the manager node.

4. Create an inventory file in the *omnia* folder. Add login node IP address under the *[login_node]* group, manager node IP address under the *[manager]* group, compute node IP addresses under the *[compute]* group, and NFS node IP address under the *[nfs_node]* group. A template file named INVENTORY is provided in the *omnia\docs* folder.  
>>	**Note**: 
>> * Omnia checks for red hat subscription being enabled on RedHat nodes as a pre-requisite. Check out [how to enable Red Hat subscription here](ENABLING_OMNIA_FEATURES.md#red-hat-subscription). Not having Red Hat subscription enabled on the manager node will cause `omnia.yml` to fail. If compute nodes do not have Red Hat subscription enabled, `omnia.yml` will skip the node entirely.
>> * Ensure that all the four groups (login_node, manager, compute, nfs_node) are present in the template, even if the IP addresses are not updated under login_node and nfs_node groups.


5. To install Omnia:

| Leap OS                     	| CentOS, Rocky, Red Hat                                       	|
|-----------------------------	|-----------------------------------------------------------	|
| `ansible-playbook omnia.yml -i inventory -e 'ansible_python_interpreter=/usr/bin/python3'`   	| `ansible-playbook omnia.yml -i inventory`	|
		
>> **Note:** Omnia creates a log file which is available at: `/var/log/omnia.log`.

6. By default, no skip tags are selected, and both Kubernetes and Slurm will be deployed.  

To skip the installation of Kubernetes, enter:  
    `ansible-playbook omnia.yml -i inventory --skip-tags "kubernetes"` 
	
To skip the installation of Slurm, enter:  
    `ansible-playbook omnia.yml -i inventory --skip-tags "slurm"`  
>> **Note**: If only Slurm is being installed on the cluster, docker credentials are not required.

>> **Warning**: LMOD and LUA are installed with Slurm when running `omnia.yml`. If LMOD and LUA are required, do not use the skip Slurm tag.

To skip the NFS client setup, enter the following command to skip the k8s_nfs_client_setup role of Kubernetes:  
    `ansible-playbook omnia.yml -i inventory --skip-tags "nfs_client"`

    The default path of the Ansible configuration file is `/etc/ansible/`. If the file is not present in the default path, then edit the `ansible_config_file_path` variable to update the configuration path.

8. To provide passwords for mariaDB Database (for Slurm accounting), Kubernetes Pod Network CIDR, and Kubernetes CNI, edit the `omnia_config.yml` file.  
>> **Note**: 
>> * Supported values for Kubernetes CNI are calico and flannel. The default value of CNI considered by Omnia is calico. 
>> * The default value of Kubernetes Pod Network CIDR is 10.244.0.0/16. If 10.244.0.0/16 is already in use within your network, select a different Pod Network CIDR. For more information, see __https://docs.projectcalico.org/getting-started/kubernetes/quickstart__.
>> * If you want to view or edit the `omnia_config.yml` file, run the following command:  
>>    - `ansible-vault view omnia_config.yml --vault-password-file .omnia_vault_key` -- To view the file. 
>>    - `ansible-vault edit omnia_config.yml --vault-password-file .omnia_vault_key` -- To edit the file.
>> * It is suggested that you use the ansible-vault view or edit commands and that you do not use the ansible-vault decrypt or encrypt commands. If you have used the ansible-vault decrypt or encrypt commands, provide 644 permission to `omnia_config.yml`.  

Omnia considers `slurm` as the default username for MariaDB.  

## Kubernetes roles

The following __kubernetes__ roles are provided by Omnia when __omnia.yml__ file is run:
- __common__ role:
    - Install common packages on manager and compute nodes
    - Docker is installed
  **Note**: Due to lack of availability, the CentOS docker repository is installed on target nodes running Redhat.
    - Deploy time ntp/chrony
    - Install Nvidia drivers and software components
>>  **Caution**: If the target node is running Rocky, Nvidia drivers will only be installed if kernel package upgrades are available. If not, the installation is skipped with a warning message.
- **k8s_common** role: 
	- Required Kubernetes packages are installed
	- Starts the docker and Kubernetes services.
- **k8s_manager** role: 
	- __helm__ package for Kubernetes is installed.
- **k8s_firewalld** role: This role is used to enable the required ports to be used by Kubernetes. 
	- For __head-node-ports__: 6443,2379-2380,10251,10250,10252
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
	- Kubernetes' services are deployed such as Kubernetes Dashboard, Prometheus, MetalLB and NFS client provisioner


* Whenever k8s_version, k8s_cni or k8s_pod_network_cidr needs to be modified after the HPC cluster is set up, the OS in the manager and compute nodes in the cluster must be re-flashed before executing omnia.yml again.
* After Kubernetes is installed and configured, few Kubernetes and calico/flannel related ports are opened in the manager and compute nodes. This is required for Kubernetes Pod-to-Pod and Pod-to-Service communications. Calico/flannel provides a full networking stack for Kubernetes pods.
* If Kubernetes Pods are unable to communicate with the servers (i.e., unable to access the Internet) when the DNS servers are not responding, then the Kubernetes Pod Network CIDR may be overlapping with the host network which is DNS issue. To resolve this issue:
	1. Disable firewalld.service.
	2. If the issue persists, then perform the following actions:  
		a. Format the OS on manager and compute nodes.  
		b. In the control plane, edit the *omnia_config.yml* file to change the Kubernetes Pod Network CIDR or CNI value. Suggested IP range is 192.168.0.0/16 and ensure you provide an IP which is not in use in your host network.  
		c. Execute `omnia.yml` and skip slurm using `--skip-tags slurm`.
	
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
	- Starting the Slurm services so that compute node communicates with manager node.
- **slurm_exporter** role: 
	- Slurm exporter is a package for exporting metrics collected from Slurm resource scheduling system to Prometheus.
	- Slurm exporter is installed on the host like Slurm, and Slurm exporter will be successfully installed only if Slurm is installed.  

## Login node roles
To enable the login node, the *login_node_required* variable must be set to "true" in the *omnia_config.yml* file.  
- **login_common** role: The firewall ports are opened on the manager and login nodes.  
- **login_server** role: FreeIPA server is installed and configured on the manager node to provide authentication using LDAP and Kerberos principles.  
- **login_node** role: For Rocky, FreeIPA client is installed and configured on the login node and is integrated with the server running on the manager node. For LeapOS, 389ds will be installed instead.

>>**Note**: If LeapOS is being deployed, login_common and login_server roles will be skipped. <br>
>> To skip the installation of:
>> * The login node: In the `omnia_config.yml` file, set the *login_node_required* variable to "false".  
>> * The FreeIPA server and client: Use `--skip-tags freeipa` while executing the *omnia.yml* file. 

### Installing JupyterHub and Kubeflow playbooks  
If you want to install JupyterHub and Kubeflow playbooks, you have to first install the JupyterHub playbook and then install the Kubeflow playbook.

Commands to install JupyterHub and Kubeflow:
* `ansible-playbook platforms/jupyterhub.yml -i inventory`
* `ansible-playbook platforms/kubeflow.yml -i inventory`

>> **Note**: When the Internet connectivity is unstable or slow, it may take more time to pull the images to create the Kubeflow containers. If the time limit is exceeded, the **Apply Kubeflow configurations** task may fail. To resolve this issue, you must redeploy Kubernetes cluster and reinstall Kubeflow by completing the following steps:
* Format the OS on manager and compute nodes.
* In the `omnia_config.yml` file, change the k8s_cni variable value from calico to flannel.
* Run the Kubernetes and Kubeflow playbooks. 


## Add a new compute node to the cluster

To update the INVENTORY file present in `omnia` directory with the new node IP address under the compute group. Ensure the other nodes which are already a part of the cluster are also present in the compute group along with the new node. Then, run `omnia.yml` to add the new node to the cluster and update the configurations of the manager node.

## Using BeeGFS on Clusters
BeeGFS is a hardware-independent POSIX parallel file system (a.k.a. Software-defined Parallel Storage) developed with a strong focus on performance and designed for ease of use, simple installation, and management. BeeGFS is created on an Available Source development model (source code is publicly available), offering a self-supported Community Edition and a fully supported Enterprise Edition with additional features and functionalities. BeeGFS is designed for all performance-oriented environments including HPC, AI and Deep Learning, Media & Entertainment, Life Sciences, and Oil & Gas (to name a few).
![BeeGFS Structure](../images/BeeGFS_Structure.jpg)

Once all the [pre-requisites](../PreRequisites/OMNIA_PreReqs.md#installing-beegfs-client) are met, run `omnia.yml` to set up BeeGFS. 
