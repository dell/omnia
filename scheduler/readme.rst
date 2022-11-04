
The scheduler role sets up `Kubernetes <https://kubernetes.io/>`_ and `Slurm <https://slurm.schedmd.com/documentation.html>`_.

**Kubernetes roles**

The following **kubernetes** roles are provided by Omnia when **omnia.yml** file is run:
- **common** role:
    - Install common packages on manager and compute nodes
    - Docker is installed
.. note:: Due to lack of availability, the CentOS docker repository is installed on target nodes running Redhat.
    - Deploy time ntp/chrony
    - Install Nvidia drivers and software components
.. warning:: If the target node is running Rocky, Nvidia drivers will only be installed if kernel package upgrades are available. If not, the installation is skipped with a warning message.
- **k8s_common** role:
	- Required Kubernetes packages are installed
	- Starts the docker and Kubernetes services.
- **k8s_manager** role:
	- **helm** package for Kubernetes is installed.
- **k8s_firewalld** role: This role is used to enable the required ports to be used by Kubernetes.
	- For **head-node-ports**: 6443,2379-2380,10251,10250,10252
	- For **compute-node-ports**: 10250,30000-32767
	- For **calico-udp-ports**: 4789
	- For **calico-tcp-ports**: 5473,179
	- For **flanel-udp-ports**: 8285,8472
- **k8s_nfs_server_setup** role:
	- A **nfs-share** directory, ``/home/k8snfs``, is created. Using this directory, compute nodes share the common files.
- **k8s_nfs_client_setup** role
- **k8s_start_manager** role:
	- Runs the ``/bin/kubeadm init`` command to initialize the Kubernetes services on manager node.
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
		c. Execute ``omnia.yml`` and skip slurm using ``--skip-tags slurm``.

**Slurm roles**

The following **Slurm** roles are provided by Omnia when **omnia.yml** file is run:
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

**Slurm job based user access**

To ensure security while running jobs on the cluster, users can be assigned permissions to access compute nodes only while their jobs are running. To enable the feature: ::

    cd omnia/scheduler
    ansible-playbook job_based_user_access.yml -i inventory

.. note::

    * The inventory queried in the above command is to be created by the user prior to running ``omnia.yml`` as ``scheduler.yml`` is invoked by ``omnia.yml``

    * Slurm and IPA client need to installed on the nodes before running this playbook.

    * Only users added to the 'slurm' group can execute slurm jobs. To add users to the group, use the command: ``usermod -a -G slurm <username>``.


