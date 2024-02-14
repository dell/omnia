Local repositories for the  cluster
=====================================

The local repository feature will help create offline repositories on control plane which all the cluster  nodes will access. ``local_repo/local_repo.yml`` runs with inputs from ``input/software_config.json`` and ``input/local_repo_config.yml``:

1. Enter the required values in the ``input/software_config.json`` file:

.. csv-table:: Parameters for Software Configuration
   :file: ../../Tables/software_config.csv
   :header-rows: 1
   :keepspace:
   :class: longtable



Below is a sample version of the file: ::

    {
        "cluster_os_type": "rhel",
        "cluster_os_version": "8.6",
        "repo_config": "always",
        "softwares": [
            {"name": "slurm", "version": "20.11.9"},
            {"name": "amd_benchmarks"},
            {"name": "k8s", "version":"1.26.9"},
            {"name": "jupyter", "version": "3.2.0"},
            {"name": "kubeflow", "version": "1.8"},
            {"name": "openldap"},
            {"name": "freeipa"},
            {"name": "beegfs", "version": "7.2.6"},
            {"name": "nfs"},
            {"name": "kserve"},
            {"name": "custom"},
            {"name": "amdgpu", "version": "5.4.6"},
            {"name": "rocm", "version": "5.4.6" },
            {"name": "nvidiagpu", "version": "latest"},
            {"name": "telemetry"},
            {"name": "network", "version": "5.4-2.4.1.3"},
            {"name": "utils"}
        ],

        "amdgpu": [
            {"name": "rocm", "version": "5.4.6" }
        ]
    }

2. Enter the required values in the ``input/local_repo_config.yml`` file:

+-------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Parameter               | Details                                                                                                                                                                                              |
+=========================+======================================================================================================================================================================================================+
| **repo_store_path**     | * The intended file path for   offline repository data.                                                                                                                                              |
|                         | * Ensure the disk partition has enough space.                                                                                                                                                        |
|      ``string``         |                                                                                                                                                                                                      |
|                         | **Default value**:    ``"/omnia_repo"``                                                                                                                                                              |
|      Required           |                                                                                                                                                                                                      |
+-------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| **user_repo_url**       | * The code ready builder URL   required for downloading packages to a RHEL control plane.                                                                                                            |
|                         | * This value is required on RHEL clusters.                                                                                                                                                           |
|      ``JSON List``      | * 'url' defines the baseurl for the repository.                                                                                                                                                      |
|                         | * 'gpgkey' defines gpgkey for the repository. If 'gpgkey' is omitted then   gpgcheck=0 is set for that repository.                                                                                   |
|      Optional           | * **Sample value**: ``- {url:   "http://crb.com/CRB/x86_64/os/",gpgkey:   "http://crb.com/CRB/x86_64/os/RPM-GPG-KEY"}``                                                                              |
+-------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| **user_registry**       | * Lists external user configured   mirror registries.                                                                                                                                                |
|                         | * For partial configurations of offline repositories, values listed here   will not be configured locally. Instead, subscriptions will be set up for the   cluster to access the images/RPMs online. |
|      ``JSON List``      | * 'host' defines the host for registry along with port where registry will   be accessible.                                                                                                          |
|                         | * 'cert_path' defines the absolution path location for certificates for   respective registry. If 'cert_path' value is omitted, an insecure registry will   be configured.                           |
|      Optional           | * **Sample value**: ::                                                                                                                                                                               |
|                         |                                                                                                                                                                                                      |
|                         |      	  - { host: 10.11.0.100:5001,   cert_path: "/home/ca.crt" }                                                                                                                                  |
|                         |      	  - { host:   registryhostname.registry.test, cert_path: "" }                                                                                                                                |
|                         |                                                                                                                                                                                                      |
|                         |                                                                                                                                                                                                      |
|                         |                                                                                                                                                                                                      |
|                         |                                                                                                                                                                                                      |
+-------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| **os_repo_url**         | * URL to a list of repositories   to be configured for Ubuntu clusters. This value is required on Ubuntu   clusters but ignored when the cluster runs RHEL or Rocky.                                 |
|                         | * When the value of ``repo_config`` in ``input/local_repo_config.yml`` is   set to ``always``, the given ``os_repo_url`` will be mirrored on the control   plane.                                    |
|      ``string``         | * When the value of ``repo_config`` in ``input/local_repo_config.yml`` is   set to ``partial`` or ``never``, the given ``os_repo_url`` is configured via   proxy on the compute nodes.               |
|                         |                                                                                                                                                                                                      |
|      Optional           | * **Sample value**: ``http://in.archive.ubuntu.com/ubuntu``                                                                                                                                          |
+-------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| **omnia_registry**      | * A list of registries from   where images will be downloaded for Omnia features.                                                                                                                    |
|                         | * All registries mentioned in ``user_registry`` will be set as mirror for   ``omnia_registry`` items.                                                                                                |
|      ``string``         | * This value is not validated by Omnia. Any errors can cause Omnia to   fail.                                                                                                                        |
|                         |                                                                                                                                                                                                      |
|      Mandatory          |      **Default value**: ::                                                                                                                                                                           |
|                         |                                                                                                                                                                                                      |
|                         |            - "registry.k8s.io"                                                                                                                                                                       |
|                         |      	   - "quay.io"                                                                                                                                                                               |
|                         |      	   - "docker.io"                                                                                                                                                                             |
|                         |                                                                                                                                                                                                      |
|                         |                                                                                                                                                                                                      |
|                         |      	                                                                                                                                                                                             |
+-------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| **omnia_repo_url_rhel** | * A list of all the repo urls   from where rpms will be downloaded for Omnia features.                                                                                                               |
|                         |      * 'url' defines the baseurl for the repository.                                                                                                                                                 |
|      ``JSON List``      |      * 'gpgkey' defines gpgkey for the repository. If 'gpgkey' is omitted, then   gpgcheck=0 is set for that repository                                                                              |
|                         |      * This value is not validated by Omnia. Any errors can cause Omnia to   fail.                                                                                                                   |
|      Required           |                                                                                                                                                                                                      |
|                         |      **Default value**: ::                                                                                                                                                                           |
|                         |                                                                                                                                                                                                      |
|                         |             - { url:   "https://download.docker.com/linux/centos/$releasever/$basearch/stable",   gpgkey: "https://download.docker.com/linux/centos/gpg" }                                           |
|                         |      	    - { url:   "https://repo.radeon.com/rocm/rhel8/{{ rocm_version }}/main",   gpgkey: "https://repo.radeon.com/rocm/rocm.gpg.key" }                                                         |
|                         |      	    - { url:   "https://download.fedoraproject.org/pub/epel/8/Everything/$basearch",   gpgkey: "https://dl.fedoraproject.org/pub/epel/RPM-GPG-KEY-EPEL-8"   }                                |
|                         |      	    - { url:   "https://repo.radeon.com/amdgpu/{{ amdgpu_version }}/rhel/{{   cluster_os_version }}/main/x86_64", gpgkey:   "https://repo.radeon.com/rocm/rocm.gpg.key" }                    |
|                         |      	    - { url:   "https://www.beegfs.io/release/beegfs_{{beegfs_version}}/dists/rhel8",   gpgkey:   "https://www.beegfs.io/release/beegfs_{{beegfs_version}}/gpg/GPG-KEY-beegfs"   }           |
|                         |      	    - { url:   "https://developer.download.nvidia.com/compute/cuda/repos/rhel8/x86_64",   gpgkey:   "https://developer.download.nvidia.com/compute/cuda/repos/rhel8/x86_64/D42D0685.pub"}    |
|                         |      	    - { url:   "https://yum.repos.intel.com/oneapi", gpgkey:   "https://yum.repos.intel.com/intel-gpg-keys/GPG-PUB-KEY-INTEL-SW-PRODUCTS.PUB"   }                                            |
|                         |      	    - { url:   "https://ltb-project.org/rpm/openldap25/$releasever/$basearch",   gpgkey: ""}                                                                                                 |
|                         |                                                                                                                                                                                                      |
|                         |                                                                                                                                                                                                      |
|                         |                                                                                                                                                                                                      |
|                         |                                                                                                                                                                                                      |
+-------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+


Alternatively, run the following commands: ::

    cd local_repo
    ansible-playbook local_repo.yml



