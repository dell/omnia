# Install Omnia using CLI

The following sections provide details on installing Omnia using CLI. If you want to install the Omnia appliance and manage workloads using the Omnia appliance, see [Install the Omnia appliance](INSTALL_OMNIA_APPLIANCE.md) and [Monitor Kubernetes and Slurm](MONITOR_CLUSTERS.md) for more information.

## Prerequisites
* Ensure that all the prerequisites listed in the [Preparation to install Omnia](PREINSTALL_OMNIA.md) are met before installing Omnia.
* If there are errors when any of the following Ansible playbook commands are run, re-run the commands again. 
* The user should have root privileges to perform installations and configurations.
 
## Install Omnia using CLI

1. Clone the Omnia repository:
``` 
git clone -b release https://github.com/dellhpc/omnia.git 
```
__Note:__ After the Omnia repository is cloned, a folder named __omnia__ is created. Ensure that you do not rename this folder.

2. Change the directory to __omnia__: `cd omnia`

3. An inventory file must be created in the __omnia__ folder. Add compute node IPs under **[compute]** group and the manager node IP under **[manager]** group. See the INVENTORY template file under `omnia\docs` folder.

4. To install Omnia:
```
ansible-playbook omnia.yml -i inventory -e "ansible_python_interpreter=/usr/bin/python2" 
```

5. By default, no skip tags are selected, and both Kubernetes and Slurm will be deployed.

To skip the installation of Kubernetes, enter:  
`ansible-playbook omnia.yml -i inventory -e "ansible_python_interpreter=/usr/bin/python2"  --skip-tags "kubernetes"` 

To skip the installation of Slurm, enter:  
`ansible-playbook omnia.yml -i inventory -e "ansible_python_interpreter=/usr/bin/python2"  --skip-tags "slurm"`  

To skip the NFS client setup, enter the following command to skip the k8s_nfs_client_setup role of Kubernetes:  
`ansible-playbook omnia.yml -i inventory -e "ansible_python_interpreter=/usr/bin/python2"  --skip-tags "nfs_client"`

6. To provide passwords for mariaDB Database (for Slurm accounting), Kubernetes Pod Network CIDR, and Kubernetes CNI, edit the `omnia_config.yml` file.  
__Note:__ 
* Supported values for Kubernetes CNI are calico and flannel. The default value of CNI considered by Omnia is calico. 
* The default value of Kubernetes Pod Network CIDR is 10.244.0.0/16. If 10.244.0.0/16 is already in use within your network, select a different Pod Network CIDR. For more information, see __https://docs.projectcalico.org/getting-started/kubernetes/quickstart__.

To view the set passwords of omnia_config.yml at a later time:  
`ansible-vault view omnia_config.yml --vault-password-file .omnia_vault_key`

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

__Note:__ 
* After Kubernetes is installed and configured, few Kubernetes and calico/flannel related ports are opened in the manager and compute nodes. This is required for Kubernetes Pod-to-Pod and Pod-to-Service communications. Calico/flannel provides a full networking stack for Kubernetes pods.
* If Kubernetes Pods are unable to communicate with the servers when the DNS servers are not responding, then the Kubernetes Pod Network CIDR may be overlapping with the host network which is DNS issue. To resolve this issue follow the below steps:
1. In your Kubernetes cluster, run `kubeadm reset -f` on the nodes.
2. In the management node, edit the `omnia_config.yml` file to change the Kubernetes Pod Network CIDR. Suggested IP range is 192.168.0.0/16 and ensure you provide an IP which is not in use in your host network.
3. Execute omnia.yml and skip slurm using --skip-tags slurm.

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
	- Slurm exporter is a package for exporting metrics collected from Slurm resource scheduling system to prometheus.
	- Slurm exporter is installed on the host like Slurm, and Slurm exporter will be successfully installed only if Slurm is installed.

**Note:** If you want to install JupyterHub and Kubeflow playbooks, you have to first install the JupyterHub playbook and then install the Kubeflow playbook.

Commands to install JupyterHub and Kubeflow:
* `ansible-playbook platforms/jupyterhub.yml -i inventory -e "ansible_python_interpreter=/usr/bin/python2"`
* `ansible-playbook platforms/kubeflow.yml -i inventory -e "ansible_python_interpreter=/usr/bin/python2" `

__Note:__ When the Internet connectivity is unstable or slow, it may take more time to pull the images to create the Kubeflow containers. If the time limit is exceeded, the Apply Kubeflow configurations task may fail. To resolve this issue, you must redeploy Kubernetes cluster and reinstall Kubeflow by completing the following steps:
* Format the OS on manager and compute nodes.
* In the omnia_config.yml file, change the k8s_cni variable value from calico to flannel.
* Run the Kubernetes and Kubeflow playbooks.

## Add a new compute node to the cluster

To update the INVENTORY file present in `omnia` directory with the new node IP address under the compute group. Ensure the other nodes which are already a part of the cluster are also present in the compute group along with the new node. Then, run`omnia.yml` to add the new node to the cluster and update the configurations of the manager node.
