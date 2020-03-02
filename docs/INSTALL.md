Dancing to the beat of a different drum.

# Short Version:

Install Kubernetes and all dependencies
```
ansible-playbook -i host_inventory_file build-kubernetes-cluster.yml
```

Initialize K8S cluster
```
ansible-playbook -i host_inventory_file build-kubernetes-cluster.yml --tags "init"
```


# What this does:

## Build/Install

### Add additional repositories:

- Kubernetes (Google)
- El Repo (nvidia drivers)
- Nvidia (nvidia-docker)
- EPEL (Extra Packages for Enterprise Linux)

### Install common packages
 - gcc
 - python-pip
 - docker
 - kubelet
 - kubeadm
 - kubectl
 - nvidia-detect
 - kmod-nvidia
 - nvidia-x11-drv
 - nvidia-container-runtime
 - ksonnet (CLI framework for K8S configs)

### Enable GPU Device Plugins (nvidia-container-runtime-hook)

### Modify kubeadm config to allow GPUs as schedulable resource 

### Start and enable services
 - Docker
 - Kubelet

## Initialize Cluster
### Head/master
- Start K8S pass startup token to compute/slaves
- Initialize networking (Currently using WeaveNet)
-Setup K8S Dashboard
- Create dynamic/persistent volumes
### Compute/slaves
- Join k8s cluster
