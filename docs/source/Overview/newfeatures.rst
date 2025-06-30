New Features
============

* Enablement of AMD 17G servers - R6725, R7725, R6715, R7715
* Enablement of Intel Gaudi 3 accelerator
* Enablement of NVIDIA accelerators - L40s, H100 NVL, H200 SXM
* Support for Ubuntu 24.04 OS
* Support for upgrading Omnia version on the OIM, from 1.7 to 1.7.1
* Support for NVIDIA GPU operator (25.3.0) on nodes running Ubuntu 24.04 OS
* Support for adding external nodes (with pre-loaded OS and internet connectivity) to a Kubernetes cluster
* Support for configuring additional NICs and updating kernel parameters during the provisioning of the cluster nodes
* Support for NVIDIA Collective Communications Library (NCCL) 2.25.1 on nodes with NVIDIA accelerators running Ubuntu 24.04 OS
* Support for ROCm Communication Collectives Library (RCCL) 2.21.5 on nodes with AMD accelerators
* Support for Multus-CNI plugin (4.1.4) and Whereabouts plugin (0.8.0) for Kubernetes (K8s)
* Support for RoCE configuration with Calico network plugin
* Updated software packages for Omnia 1.7.1 (compared to 1.7):


    +--------------------------+-----------------------------------+-------------------------------+
    | Software package         | Current Version (1.7.1)           | Previous Version (1.7)        |
    +==========================+===================================+===============================+
    | Kubernetes               | 1.31.4                            | 1.29.5                        |
    +--------------------------+-----------------------------------+-------------------------------+
    | Kubespray                | 2.27                              | 2.25                          |
    +--------------------------+-----------------------------------+-------------------------------+
    | Intel Gaudi driver       | 1.21.1                            | 1.19.2                        |
    +--------------------------+-----------------------------------+-------------------------------+
    | CSI PowerScale driver    | 2.13.0                            | 2.11.0                        |
    +--------------------------+-----------------------------------+-------------------------------+
    | NVIDIA CUDA              | 12.8                              | 2.13.2                        |
    +--------------------------+-----------------------------------+-------------------------------+
    | NVIDIA vLLM              | 0.7.2                             | 0.4.0                         |
    +--------------------------+-----------------------------------+-------------------------------+
    | AMD ROCm                 | 6.3.1                             | 6.2.2                         |
    +--------------------------+-----------------------------------+-------------------------------+
    | Grafana                  | 11.4.1                            | 8.3.2                         |
    +--------------------------+-----------------------------------+-------------------------------+
    | BCM RoCE                 | 232.1.133.2                       | 230.2.54.0                    |
    +--------------------------+-----------------------------------+-------------------------------+

