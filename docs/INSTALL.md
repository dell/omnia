## TL;DR Installation
 
### Kubernetes
Install Kubernetes and all dependencies
```
ansible-playbook -i kubernetes/host_inventory_file kubernetes/kubernetes.yml
```

Initialize K8s cluster
```
ansible-playbook -i kubernetes/host_inventory_file kubernetes/kubernetes.yml --tags "init"
```

### Install Kubeflow 
```
ansible-playbook -i kubernetes/host_inventory_file kubernetes/kubeflow.yaml
```

### Slurm
```
ansible-playbook -i slurm/slurm_inventory_file slurm/slurm.yml
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

`manager` playbook
* Install Helm v3
* (optional) add firewall rules for Slurm and kubernetes

Everything from this point on can be called by using the `init` tag
```
ansible-playbook -i kubernetes/host_inventory_file kubernetes/kubernetes.yml --tags "init"
```

`startmanager` playbook
* turn off swap
*Initialize Kubernetes
    * Head/manager
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

