Local repositories for the  cluster
=====================================

The local repository feature will help create offline repositories on the control plane which all the cluster nodes will access. ``local_repo/local_repo.yml`` runs with inputs from ``input/software_config.json`` and ``input/local_repo_config.yml``:

1. Enter the required values in the ``input/software_config.json`` file:

.. csv-table:: Parameters for Software Configuration
   :file: ../../Tables/software_config.csv
   :header-rows: 1
   :keepspace:
   :class: longtable



Below is a sample version of the file: ::

    {
        "cluster_os_type": "ubuntu",
        "cluster_os_version": "22.04",
        "repo_config": "partial",
        "softwares": [
            {"name": "k8s", "version":"1.26.12"},
            {"name": "jupyter", "version": "3.2.0"},
            {"name": "kubeflow", "version": "1.8"},
            {"name": "openldap"},
            {"name": "beegfs", "version": "7.2.6"},
            {"name": "nfs"},
            {"name": "kserve"},
            {"name": "custom"},
            {"name": "amdgpu", "version": "6.0"},
            {"name": "cuda", "version": "12.3.2"},
            {"name": "ofed", "version": "24.01-0.3.3.1"},
            {"name": "telemetry"},
            {"name": "utils"},
            {"name": "vllm"},
            {"name": "pytorch"},
            {"name": "tensorflow"},
            {"name": "bcm_roce", "version": "229.2.9.0"}
        ],

        "amdgpu": [
            {"name": "rocm", "version": "6.0" }
        ],
    	"vllm": [
    		{"name": "vllm_amd", "version":"vllm-v0.2.4"},
    		{"name": "vllm_nvidia", "version": "latest"}
    	],
    	"pytorch": [
    		{"name": "pytorch_cpu", "version":"latest"},
    		{"name": "pytorch_amd", "version":"latest"},
    		{"name": "pytorch_nvidia", "version": "23.12-py3"}
    	],
    	"tensorflow": [
    		{"name": "tensorflow_cpu", "version":"latest"},
    		{"name": "tensorflow_amd", "version":"latest"},
    		{"name": "tensorflow_nvidia", "version": "23.12-tf2-py3"}
    	]

    }


For a list of accepted values in ``softwares``, go to ``input/config/<operating_system>/<operating_system_version>`` and view the list of JSON files available. The filenames present in this location (without the * .json extension) are a list of accepted software names. The repositories to be downloaded for each software are listed the corresponding JSON file. For example: For a cluster running RHEL 8.8, go to ``input/config/rhel/8.8/`` and view the file list:

::

    amdgpu.json
    k8s.json
    openldap.json
    rocm.json

For a list of repositories (and their types) configured for kubernetes, view the ``k8s.json``` file: ::

    {

      "k8s": {

        "cluster": [
        {
          "package": "containerd.io-1.6.16-3.1.el8",
          "type": "rpm",
          "repo_name": "docker-ce-repo"
        },
        {
          "package": "kubelet",
          "type": "tarball",
          "url": "https://dl.k8s.io/release/v{{ k8s_version }}/bin/linux/amd64/kubelet"
        },
        {
          "package": "kubeadm",
          "type": "tarball",
          "url": "https://dl.k8s.io/release/v{{ k8s_version }}/bin/linux/amd64/kubeadm"
        },
        {
          "package": "helm",
          "type": "tarball",
          "url": "https://get.helm.sh/helm-v3.12.3-linux-amd64.tar.gz"
        },
        {
          "package": "registry.k8s.io/kube-apiserver",
          "version": "v{{ k8s_version }}",
          "type": "image"
        },
        {
          "package": "registry.k8s.io/kube-controller-manager",
          "version": "v{{ k8s_version }}",
          "type": "image"
        },
        {
          "package": "quay.io/coreos/etcd",
          "version": "v3.5.9",
          "type": "image"
        },
        {
          "package": "quay.io/calico/node",
          "version": "v3.25.2",
          "type": "image"
        },
        {
          "package": "registry.k8s.io/pause",
          "version": "3.9",
          "type": "image"
        },
        {
          "package": "docker.io/kubernetesui/dashboard",
          "version": "v2.7.0",
          "type": "image"
        }
        ]

      }

    }

.. note:: To configure a locally available repository that does not have a pre-defined json file, `click here <CustomLocalRepo.html>`_.

2. Enter the required values in the ``input/local_repo_config.yml`` file:

    +-------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | Parameter               | Details                                                                                                                                                                                           |
    +=========================+===================================================================================================================================================================================================+
    | **repo_store_path**     | * The intended file path for   offline repository data.                                                                                                                                           |
    |                         | * Ensure the disk partition has enough space.                                                                                                                                                     |
    |      ``string``         |                                                                                                                                                                                                   |
    |                         | **Default value**:    ``"/omnia_repo"``                                                                                                                                                           |
    |      Required           |                                                                                                                                                                                                   |
    +-------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | **user_repo_url**       | * This variable accepts the repository urls of the user which contains the packages required for the cluster.                                                                                     |
    |                         | * When ``repo_config`` is always, the given list will be configured on the control plane and packages required for cluster will be downloaded into a local repository.                            |
    |      ``JSON List``      | * When ``repo_config`` is partial, a local repository is created on the control plane containing packages that are not part of the user's repository.                                             |
    |                         | * When ``repo_config`` is never, no local repository is created and packages are downloaded on all cluster nodes.                                                                                 |
    |      Optional           | * 'url' defines the baseurl for the repository.                                                                                                                                                   |
    |                         | * 'gpgkey' defines gpgkey for the repository. If 'gpgkey' is omitted then   gpgcheck=0 is set for that repository.                                                                                |
    |                         |                                                                                                                                                                                                   |
    |                         | **Sample value**:  ``- {url:   "http://crb.com/CRB/x86_64/os/",gpgkey:   "http://crb.com/CRB/x86_64/os/RPM-GPG-KEY"}``                                                                            |
    +-------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | **user_registry**       | * This variable accepts the registry url along with port of the user which contains the images required for cluster.                                                                              |
    |                         | * When ``repo_config`` is always, the list given in ``user_registry`` will be configured on the control plane and packages required for cluster will be downloaded into a local repository.       |
    |      ``JSON List``      | * When ``repo_config`` is partial, a local registry is created on the control plane containing packages that are not part of the ``user_registry``.                                               |
    |                         | * When ``repo_config`` is never, no local registry is created and packages are downloaded on all cluster nodes.                                                                                   |
    |      Optional           | * 'host' defines the URL and path to the registry.                                                                                                                                                |
    |                         | * 'cert_path' defines the absolute path where the security certificates for each registry. If this path is not provided, insecure registries are configured.                                      |
    |                         |                                                                                                                                                                                                   |
    |                         | **Sample value**:  ``- {host:   10.11.0.100:5001, cert_path:   "/home/ca.crt"}``                                                                                                                  |
    +-------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | **ubuntu_os_url**       | * This variable defines the repositories to be configured on all the compute nodes.                                                                                                               |
    |                         | * This variable is required if the cluster runs on Ubuntu and ignored if the cluster runs on RHEL or Rocky.                                                                                       |
    |   ``string``            | * When ``repo_config`` is ``always``, the given ``ubuntu_os_url`` is mirrored on the control plane.                                                                                               |
    |                         | * When ``repo_config`` is ``partial`` or ``never``, the given ``ubuntu_os_url`` is configured via proxy on the cluster nodes.                                                                     |
    |                         | * **Sample Values**: ``http://in.archive.ubuntu.com/ubuntu``                                                                                                                                      |
    |     Optional            |                                                                                                                                                                                                   |
    +-------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | **rhel_os_url**         | * This variable defines the code ready builder URL to be configured on all the compute nodes.                                                                                                     |
    |                         | * This variable is required if the cluster runs on RHEL and ignored if the cluster runs on Ubuntu or Rocky.                                                                                       |
    |   ``string``            | * When ``repo_config`` is ``always``, the given ``ubuntu_os_url`` is mirrored on the control plane.                                                                                               |
    |                         | * When ``repo_config`` is ``partial`` or ``never``, the given ``ubuntu_os_url`` is configured via proxy on the cluster nodes.                                                                     |
    |   Optional              | * **Sample Values**: ``- {url: "http://crb.com/CRB/x86_64/os/",gpgkey: "http://crb.com/CRB/x86_64/os/RPM-GPG-KEY"}``                                                                              |
    +-------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | **omnia_registry**      | * A list of registries from   where images will be downloaded for Omnia features.                                                                                                                 |
    |                         | * All registries mentioned in ``user_registry`` will be set as mirror for   ``omnia_registry`` items.                                                                                             |
    |      ``string``         | * This value is not validated by Omnia. Any errors can cause Omnia to   fail.                                                                                                                     |
    |                         |                                                                                                                                                                                                   |
    |      Mandatory          | * **Default value**: ::                                                                                                                                                                           |
    |                         |                                                                                                                                                                                                   |
    |                         |            - "registry.k8s.io"                                                                                                                                                                    |
    |                         |            - "quay.io"                                                                                                                                                                            |
    |                         |            - "docker.io"                                                                                                                                                                          |
    |                         |                                                                                                                                                                                                   |
    |                         |                                                                                                                                                                                                   |
    |                         |                                                                                                                                                                                                   |
    +-------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | **omnia_repo_url_rhel** | * A list of all the repo urls   from where rpms will be downloaded for Omnia features.                                                                                                            |
    |                         | * 'url' defines the baseurl for the repository.                                                                                                                                                   |
    |      ``JSON List``      | * 'gpgkey' defines gpgkey for the repository. If 'gpgkey' is omitted, then   gpgcheck=0 is set for that repository                                                                                |
    |                         | * This value is not validated by Omnia. Any errors can cause Omnia to   fail.                                                                                                                     |
    |      Required           |                                                                                                                                                                                                   |
    |                         | * **Default value**: ::                                                                                                                                                                           |
    |                         |                                                                                                                                                                                                   |
    |                         |             - { url:   "https://download.docker.com/linux/centos/$releasever/$basearch/stable",   gpgkey: "https://download.docker.com/linux/centos/gpg" }                                        |
    |                         |             - { url:   "https://repo.radeon.com/rocm/rhel8/{{ rocm_version }}/main",   gpgkey: "https://repo.radeon.com/rocm/rocm.gpg.key" }                                                      |
    |                         |             - { url:   "https://download.fedoraproject.org/pub/epel/8/Everything/$basearch",   gpgkey: "https://dl.fedoraproject.org/pub/epel/RPM-GPG-KEY-EPEL-8"   }                             |
    |                         |             - { url:   "https://repo.radeon.com/amdgpu/{{ amdgpu_version }}/rhel/{{   cluster_os_version }}/main/x86_64", gpgkey:   "https://repo.radeon.com/rocm/rocm.gpg.key" }                 |
    |                         |             - { url:   "https://www.beegfs.io/release/beegfs_{{beegfs_version}}/dists/rhel8",   gpgkey:   "https://www.beegfs.io/release/beegfs_{{beegfs_version}}/gpg/GPG-KEY-beegfs"   }        |
    |                         |             - { url:   "https://developer.download.nvidia.com/compute/cuda/repos/rhel8/x86_64",   gpgkey:   "https://developer.download.nvidia.com/compute/cuda/repos/rhel8/x86_64/D42D0685.pub"} |
    |                         |             - { url:   "https://yum.repos.intel.com/oneapi", gpgkey:   "https://yum.repos.intel.com/intel-gpg-keys/GPG-PUB-KEY-INTEL-SW-PRODUCTS.PUB"   }                                         |
    |                         |             - { url:   "https://ltb-project.org/rpm/openldap25/$releasever/$basearch",   gpgkey: ""}                                                                                              |
    |                         |                                                                                                                                                                                                   |
    |                         |                                                                                                                                                                                                   |
    |                         |                                                                                                                                                                                                   |
    |                         |                                                                                                                                                                                                   |
    +-------------------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

3. Run the following commands: ::

    cd local_repo
    ansible-playbook local_repo.yml

.. toctree::
    Prerequisite
    cuda
    ofed
    bcm_roce
    CustomLocalRepo



