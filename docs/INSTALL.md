# Installing Omnia

## TL;DR

### Kubernetes
Install Kubernetes and all dependencies
```
ansible-playbook -i host_inventory_file kubernetes/kubernetes.yml
```

Initialize K8s cluster
```
ansible-playbook -i host_inventory_file kubernetes/kubernetes.yml --tags "init"
```
### Slurm
```
ansible-playbook -i host_inventory_file slurm/slurm.yml
```

## Build/Install
### Kubernetes

- Add additional repositories:

-- Kubernetes (Google)
-- El Repo (nvidia drivers)
-- Nvidia (nvidia-docker)
-- EPEL (Extra Packages for Enterprise Linux)

- Install common packages
-- gcc
-- python-pip
-- docker
-- kubelet
-- kubeadm
-- kubectl
-- nvidia-detect
-- kmod-nvidia
-- nvidia-x11-drv
-- nvidia-container-runtime
-- ksonnet (CLI framework for K8S configs)

- Enable GPU Device Plugins (nvidia-container-runtime-hook)

- Modify kubeadm config to allow GPUs as schedulable resource 

- Start and enable services
-- Docker
-- Kubelet

- Initialize Cluster
-- Head/master
--- Start K8S pass startup token to compute/slaves
--- Initialize networking (Currently using WeaveNet)
--- Setup K8S Dashboard
--- Create dynamic/persistent volumes
-- Compute/slaves
--- Join k8s cluster
