Input parameters for Local Repositories
----------------------------------------

* Input all required values in ``input/software_config.json``.

    .. csv-table:: Parameters for Software Configuration
       :file: ../../Tables/software_config.csv
       :header-rows: 1
       :keepspace:
       :class: longtable



* Input the required values in ``input/local_repo_config.yml``.

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
        |   ``string``            | * When ``repo_config`` is ``always``, the given ``rhel_os_url`` is mirrored on the control plane.                                                                                                 |
        |                         | * When ``repo_config`` is ``partial`` or ``never``, the given ``rhel_os_url`` is configured via proxy on the cluster nodes.                                                                       |
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

