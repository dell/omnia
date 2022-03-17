# Install Omnia using CLI

The following sections provide details on installing Omnia using CLI.  

To install the Omnia control plane and manage workloads on your cluster using the Omnia control plane, see [Install the Omnia Control Plane](INSTALL_OMNIA_CONTROL_PLANE.md) and [Monitor Kubernetes and Slurm](MONITOR_CLUSTERS.md) for more information.

## Prerequisites
* The login, manager, and compute nodes must be running CentOS 7.9 2009 OS/ Rocky 8.x/ LeapOS 15.3.
>> __Note:__ If you are using LeapOS, the following repositories will be enabled when running `omnia.yml`:
>> * OSS ([Repository](http://download.opensuse.org/distribution/leap/15.3/repo/oss/) + [Update](http://download.opensuse.org/update/leap/15.3/oss/))
>> * Non-OSS ([Repository](http://download.opensuse.org/distribution/leap/15.3/repo/non-oss/) + [Update](http://download.opensuse.org/update/leap/15.3/non-oss/))
* If you have configured the `omnia_config.yml` file to enable the login node, the login node must be part of the cluster. 
* All nodes must be connected to the network and must have access to the Internet.
* Set the hostnames of all the nodes in the cluster.
	* If the login node is enabled, then set the hostnames in the format: __hostname.domainname__. For example, "manager.omnia.test" is a valid hostname. **Do not** use underscores ( _ ) in the host names.
	* Include the hostnames under /etc/hosts in the format: </br>*ipaddress hostname.domainname*. For example, "192.168.12.1 manager.example.com" is a valid entry.
* SSH Keys for root are installed on all nodes to allow for password-less SSH.
* The user should have root privileges to perform installations and configurations.
* On the management station, ensure that you install Python 3.6 and Ansible.  
	* Run the following commands to install Python 3.6:  
		```
		dnf install epel-release -y
		dnf install python3 -y
		```
	* Run the following commands to install Ansible:
		 ```
		 pip3.6 install --upgrade pip
		 python3.6 -m pip install ansible
		 ```
	After the installation is complete, run `ansible --version` to verify if the installation is successful. In the output, ensure that the executable location path is present in the PATH variable by running `echo $PATH`.
	If the executable location path is not available, update the path by running `export PATH=$PATH:<executable location>\`.  
	
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
	
>> **Note**: To deploy Omnia, Python 3.6 provides bindings to system tools such as RPM, DNF, and SELinux. As versions greater than 3.6 do not provide these bindings to system tools, ensure that you install Python 3.6 with dnf.  

>> **Note**: If Ansible version 2.9 or later is installed, ensure it is uninstalled before installing a newer version of Ansible. Run the following commands to uninstall Ansible before upgrading to a newer version.  
>> 1. `pip uninstall ansible`
>> 2. `pip uninstall ansible-base (if ansible 2.9 is installed)`
>> 3. `pip uninstall ansible-core (if ansible 2.10  > version is installed)`

	 
* On the management station, run the following commands to install Git:
	```
	dnf install epel-release -y
	dnf install git -y
	```

>> **Note**: If there are errors while executing the Ansible playbook commands, then re-run the commands.  

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

>> __Note:__ After the Omnia repository is cloned, a folder named __omnia__ is created. Ensure that you do not rename this folder.

2. Change the directory to __omnia__: `cd omnia`

3. In the `omnia_config.yml` file, provide the following details:  

| Parameter Name             | Default Value | Additional Information                                                                                                                                                                                                                               |
|----------------------------|---------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| mariadb_password           | password      | Password used to access the Slurm database. <br> Required Length: 8   characters <br> The password must not contain -,\, ',"                                                                                                                         |
| k8s_version                | 1.16.7        | Kuberenetes Version <br> Accepted Values: "1.16.7" or   "1.19.3"                                                                                                                                                                                     |
| k8s_cni                    | calico        | CNI type used by Kuberenetes. <br> Accepted values: calico, flannel                                                                                                                                                                                  |
| k8s_pod_network_cidr       | 10.244.0.0/16 | Kubernetes pod network CIDR                                                                                                                                                                                                                          |
| docker_username            |               | Username to login to Docker. A kubernetes secret will be created and   patched to the service account in default namespace. <br> This value is   optional but suggested to avoid docker pull limit issues                                            |
| docker_password            |               | Password to login to Docker <br> This value is mandatory if a   docker_username is provided                                                                                                                                                          |
| ansible_config_file_path   | /etc/ansible  | Path where the ansible.cfg file can be found. <br> If `dnf` is   used, the default value is valid. If `pip` is used, the variable must be set   manually                                                                                             |
| login_node_required        | TRUE          | Boolean indicating whether the login node is required or not                                                                                                                                                                                         |
| domain_name                | omnia.test    | Sets the intended domain name                                                                                                                                                                                                                        |
| realm_name                 | OMNIA.TEST    | Sets the intended realm name                                                                                                                                                                                                                         |
| directory_manager_password |               | Password authenticating admin level access to the Directory for system   management tasks. It will be added to the instance of directory server   created for IPA. <br> Required Length: 8 characters. <br> The   password must not contain -,\, '," |
| kerberos_admin_password         |               | "admin" user password for the IPA server on RockyOS. If LeapOS is in use, it is used as the "kerberos admin" user password for 389-ds <br> This field is not relevant to Management Stations running `LeapOS`                                                                                                                                                                                                                            |
| enable_secure_login_node   |  **false**, true             | Boolean value deciding whether security features are enabled on the Login Node. For more information, see [here](docs/Security/Enable_Security_LoginNode.md).                                                                                                                                                                                                                           |
	
	
>> __NOTE:__  Without the login node, Slurm jobs can be scheduled only through the manager node.

4. Create an inventory file in the *omnia* folder. Add login node IP address under the *[login_node]* group, manager node IP address under the *[manager]* group, compute node IP addresses under the *[compute]* group, and NFS node IP address under the *[nfs_node]* group. A template file named INVENTORY is provided in the *omnia\docs* folder.  
>>	**NOTE**: Ensure that all the four groups (login_node, manager, compute, nfs_node) are present in the template, even if the IP addresses are not updated under login_node and nfs_node groups. 

5. To install Omnia:

| Leap OS                     	| CentOS, Rocky                                             	|
|-----------------------------	|-----------------------------------------------------------	|
| `ansible-playbook omnia.yml -i inventory -e 'ansible_python_interpreter=/usr/bin/python3'`   	| `ansible-playbook omnia.yml -i inventory`	|
		


6. By default, no skip tags are selected, and both Kubernetes and Slurm will be deployed.  

	To skip the installation of Kubernetes, enter:  
	`ansible-playbook omnia.yml -i inventory --skip-tags "kubernetes"` 
	
	To skip the installation of Slurm, enter:  
	`ansible-playbook omnia.yml -i inventory --skip-tags "slurm"`  

	To skip the NFS client setup, enter the following command to skip the k8s_nfs_client_setup role of Kubernetes:  
	`ansible-playbook omnia.yml -i inventory --skip-tags "nfs_client"`

	The default path of the Ansible configuration file is `/etc/ansible/`. If the file is not present in the default path, then edit the `ansible_config_file_path` variable to update the configuration path.

7. To provide passwords for mariaDB Database (for Slurm accounting), Kubernetes Pod Network CIDR, and Kubernetes CNI, edit the `omnia_config.yml` file.  
>> __Note:__ 
* Supported values for Kubernetes CNI are calico and flannel. The default value of CNI considered by Omnia is calico. 
* The default value of Kubernetes Pod Network CIDR is 10.244.0.0/16. If 10.244.0.0/16 is already in use within your network, select a different Pod Network CIDR. For more information, see __https://docs.projectcalico.org/getting-started/kubernetes/quickstart__.

>> **NOTE**: If you want to view or edit the `omnia_config.yml` file, run the following command:  
- `ansible-vault view omnia_config.yml --vault-password-file .omnia_vault_key` -- To view the file. 
- `ansible-vault edit omnia_config.yml --vault-password-file .omnia_vault_key` -- To edit the file.

>> **NOTE**: It is suggested that you use the ansible-vault view or edit commands and that you do not use the ansible-vault decrypt or encrypt commands. If you have used the ansible-vault decrypt or encrypt commands, provide 644 permission to `omnia_config.yml`.  

Omnia considers `slurm` as the default username for MariaDB.  

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
	- Kubernetes services are deployed such as Kubernetes Dashboard, Prometheus, MetalLB and NFS client provisioner


* Whenever k8s_version, k8s_cni or k8s_pod_network_cidr needs to be modified after the HPC cluster is setup, the OS in the manager and compute nodes in the cluster must be re-flashed before executing omnia.yml again.
* After Kubernetes is installed and configured, few Kubernetes and calico/flannel related ports are opened in the manager and compute nodes. This is required for Kubernetes Pod-to-Pod and Pod-to-Service communications. Calico/flannel provides a full networking stack for Kubernetes pods.
* If Kubernetes Pods are unable to communicate with the servers (i.e., unable to access the Internet) when the DNS servers are not responding, then the Kubernetes Pod Network CIDR may be overlapping with the host network which is DNS issue. To resolve this issue:
	1. Disable firewalld.service.
	2. If the issue persists, then perform the following actions:  
		a. Format the OS on manager and compute nodes.  
		b. In the management station, edit the *omnia_config.yml* file to change the Kubernetes Pod Network CIDR or CNI value. Suggested IP range is 192.168.0.0/16 and ensure you provide an IP which is not in use in your host network.  
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

>>__Note:__ If LeapOS is being deployed, login_common and login_server roles will be skipped.  

>> **NOTE**: To skip the installation of:
>> * The login node-In the `omnia_config.yml` file, set the *login_node_required* variable to "false".  
>> * The FreeIPA server and client: Use `--skip-tags freeipa` while executing the *omnia.yml* file. 

### Installing JupyterHub and Kubeflow playbooks  
If you want to install JupyterHub and Kubeflow playbooks, you have to first install the JupyterHub playbook and then install the Kubeflow playbook.

Commands to install JupyterHub and Kubeflow:
* `ansible-playbook platforms/jupyterhub.yml -i inventory`
* `ansible-playbook platforms/kubeflow.yml -i inventory`

>> __Note:__ When the Internet connectivity is unstable or slow, it may take more time to pull the images to create the Kubeflow containers. If the time limit is exceeded, the **Apply Kubeflow configurations** task may fail. To resolve this issue, you must redeploy Kubernetes cluster and reinstall Kubeflow by completing the following steps:
* Format the OS on manager and compute nodes.
* In the `omnia_config.yml` file, change the k8s_cni variable value from calico to flannel.
* Run the Kubernetes and Kubeflow playbooks. 


## Add a new compute node to the cluster

To update the INVENTORY file present in `omnia` directory with the new node IP address under the compute group. Ensure the other nodes which are already a part of the cluster are also present in the compute group along with the new node. Then, run `omnia.yml` to add the new node to the cluster and update the configurations of the manager node.

