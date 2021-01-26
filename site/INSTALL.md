## TL;DR Installation
 
### Kubernetes
Install Slurm and Kubernetes, along with all dependencies
```
ansible-playbook -i host_inventory_file omnia.yml
```

Install Slurm only
```
ansible-playbook -i host_inventory_file omnia.yml --skip-tags "k8s"
```

Install Kubernetes only
```
ansible-playbook -i host_inventory_file omnia.yml --skip-tags "slurm"
 

Initialize Kubernetes cluster (packages already installed)
```
ansible-playbook -i host_inventory_file omnia.yml --skip-tags "slurm" --tags "init"
```

### Install Kubeflow 
```
ansible-playbook -i host_inventory_file platforms/kubeflow.yml
```

# Omnia  
Omnia is a collection of [Ansible](https://www.ansible.com/) playbooks which perform:
* Installation of [Slurm](https://slurm.schedmd.com/) and/or [Kubernetes](https://kubernetes.io/) on servers already provisioned with a standard [CentOS](https://www.centos.org/) image.
* Installation of auxiliary scripts for administrator functions such as moving nodes between Slurm and Kubernetes personalities.

Omnia playbooks perform several tasks:
`common` playbook handles installation of software 
* Add yum repositories:
    - Kubernetes (Google)
    - El Repo (for Nvidia drivers)
    - EPEL (Extra Packages for Enterprise Linux)
* Install Packages from repos:
    - bash-completion
    - docker
    - gcc
    - python-pip
    - kubelet
    - kubeadm
    - kubectl
    - nfs-utils
    - nvidia-detect
    - yum-plugin-versionlock
* Restart and enable system level services
    - Docker
    - Kubelet

`computeGPU` playbook installs Nvidia drivers and nvidia-container-runtime-hook
* Add yum repositories:
    - Nvidia (container runtime)
* Install Packages from repos:
    - kmod-nvidia
    - nvidia-container-runtime-hook
* Restart and enable system level services
    - Docker
    - Kubelet
* Configuration:
    - Enable GPU Device Plugins (nvidia-container-runtime-hook)
    - Modify kubeadm config to allow GPUs as schedulable resource 
* Restart and enable system level services
    - Docker
    - Kubelet

`master` playbook
* Install Helm v3
* (optional) add firewall rules for Slurm and kubernetes

Everything from this point on can be called by using the `init` tag
```
ansible-playbook -i host_inventory_file kubernetes/kubernetes.yml --tags "init"
```

`startmaster` playbook
* turn off swap
*Initialize Kubernetes
    * Head/master
        - Start K8S pass startup token to compute/slaves
        - Initialize software defined networking (Calico)

`startworkers` playbook
* turn off swap
* Join k8s cluster

`startservices` playbook
* Setup K8S Dashboard
* Add `stable` repo to helm
* Add `jupyterhub` repo to helm
* Update helm repos
* Deploy NFS client Provisioner
* Deploy Jupyterhub
* Deploy Prometheus
* Install MPI Operator


### Slurm
* Downloads and builds Slurm from source
* Install package dependencies
    - Python3
    - munge
    - MariaDB
    - MariaDB development libraries
* Build Slurm configuration files

