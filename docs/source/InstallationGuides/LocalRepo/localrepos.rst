Configuring specific local repositories
-----------------------------------------

**AMDGPU ROCm**

    To install ROCm, do the following:

        * Include the following line under ``softwares`` in ``input/software_config.json``:

            ::

                {"name": "amdgpu", "version": "6.0"},

        * Add the following line below the ``softwares`` section:

            ::

                "amdgpu": [
                                {"name": "rocm", "version": "6.0" }
                          ]

        * A sample format is available `here. </InputParameters.html>`_

**BCM RoCE**


    To install RoCE, do the following:

        * Include the following line under ``softwares`` in ``input/software_config.json``:

            ::

                {"name": "bcm_roce", "version": "229.2.61.0"}

        * Add the following line below the ``softwares`` section:

            ::

                "bcm_roce": [
                                    {"name": "bcm_roce_libraries", "version": "229.2.61.0"}
                            ],

        * A sample format is available `here. </InputParameters.html>`_


    For a list of repositories (and their types) configured for RoCE, view the ``input/config/ubuntu/<operating_system_version>/bcm_roce.json`` file. To customize your RoCE installation, update the file. URLs for different versions can be found `here <https://downloads.dell.com>`_: ::

            {
              "bcm_roce": {
                "cluster": [
                  {
                    "package": "bcm_roce_driver_{{ bcm_roce_version }}",
                    "type": "tarball",
                    "url": "",
                    "path": ""
                  }
                ]
              },
              "bcm_roce_libraries": {
                "cluster": [
                  {
                    "package": "bcm_roce_source_{{ bcm_roce_libraries_version }}",
                    "type": "tarball",
                    "url": "",
                    "path": ""
                  },
                  {"package": "libelf-dev", "type": "deb", "repo_name": "jammy"},
                  {"package": "gcc", "type": "deb", "repo_name": "jammy"},
                  {"package": "make", "type": "deb", "repo_name": "jammy"},
                  {"package": "libtool", "type": "deb", "repo_name": "jammy"},
                  {"package": "autoconf", "type": "deb", "repo_name": "jammy"},
                  {"package": "librdmacm-dev", "type": "deb", "repo_name": "jammy"},
                  {"package": "rdmacm-utils", "type": "deb", "repo_name": "jammy"},
                  {"package": "infiniband-diags", "type": "deb", "repo_name": "jammy"},
                  {"package": "ibverbs-utils", "type": "deb", "repo_name": "jammy"},
                  {"package": "perftest", "type": "deb", "repo_name": "jammy"},
                  {"package": "ethtool", "type": "deb", "repo_name": "jammy"},
                  {"package": "libibverbs-dev", "type": "deb", "repo_name": "jammy"},
                  {"package": "rdma-core", "type": "deb", "repo_name": "jammy"},
                  {"package": "strace", "type": "deb", "repo_name": "jammy"}
                ]
              }
            }


    .. note::
        * The RoCE driver is only supported on Ubuntu clusters.
        * The only accepted URL for the RoCE driver is from the Dell Driver website.

**BeeGFS**

    To install BeeGFS, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "beegfs", "version": "7.4.2"},

For information on deploying BeeGFS after setting up the cluster, `click here. <../../Roles/Storage/index.html>`_

**CUDA**

    To install CUDA, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "cuda", "version": "12.3.2"},


    For a list of repositories (and their types) configured for CUDA, view the ``input/config/<operating_system>/<operating_system_version>/cuda.json`` file. To customize your CUDA installation, update the file. URLs for different versions can be found `here <https://developer.nvidia.com/cuda-downloads>`_:

    For Ubuntu: ::

            {
                "cuda": {
                  "cluster": [
                    { "package": "cuda",
                      "type": "iso",
                      "url": "https://developer.download.nvidia.com/compute/cuda/12.3.2/local_installers/cuda-repo-ubuntu2204-12-3-local_12.3.2-545.23.08-1_amd64.deb",
                      "path": ""
                    }
                  ]
                }
            }

    For RHEL or Rocky: ::

            {
              "cuda": {
                "cluster": [
                  { "package": "cuda",
                    "type": "iso",
                    "url": "https://developer.download.nvidia.com/compute/cuda/12.3.2/local_installers/cuda-repo-rhel8-12-3-local-12.3.2_545.23.08-1.x86_64.rpm",
                    "path": ""
                  },
                  { "package": "dkms",
                    "type": "rpm",
                    "repo_name": "epel"
                  }
                ]
              }
            }


    .. note::
    * If the package version is customized, ensure that the ``version`` value is updated in ``software_config.json```.
    * If the target cluster runs on RHEL or Rocky, ensure the "dkms" package is included in ``input/config/<operating systen>/8.x/cuda.json`` as illustrated above.

**Custom repositories**

    Include the following line under ``softwares`` in ``input/software_config.json``: ::

                {"name": "custom"},

    Create a ``custom.json`` file in the following directory: ``input/config/<operating_system>/<operating_system_version>`` to define the repositories. For example, For a cluster running RHEL 8.8, go to ``input/config/rhel/8.8/`` and create the file there. The file is a JSON list consisting of the package name, repository type, URL (optional), and version (optional). Below is a sample version of the file: ::

            {
              "custom": {
                "cluster": [
                  {
                    "package": "ansible==5.3.2",
                    "type": "pip_module"
                  },
                  {
                    "package": "docker-ce-24.0.4",
                    "type": "rpm",
                    "repo_name": "docker-ce-repo"
                  },

                  {
                    "package": "gcc",
                    "type": "rpm",
                    "repo_name": "appstream"
                  },
                  {
                    "package": "community.general",
                    "type": "ansible_galaxy_collection",
                    "version": "4.4.0"
                  },

                  {
                    "package": "perl-Switch",
                    "type": "rpm",
                    "repo_name": "codeready-builder"
                  },
                  {
                    "package": "prometheus-slurm-exporter",
                    "type": "git",
                    "url": "https://github.com/vpenso/prometheus-slurm-exporter.git",
                    "version": "master"
                  },
                  {
                    "package": "ansible.utils",
                    "type": "ansible_galaxy_collection",
                    "version": "2.5.2"
                  },
                  {
                    "package": "prometheus-2.23.0.linux-amd64",
                    "type": "tarball",
                    "url": "https://github.com/prometheus/prometheus/releases/download/v2.23.0/prometheus-2.23.0.linux-amd64.tar.gz"
                  },
                  {
                    "package": "metallb-native",
                    "type": "manifest",
                    "url": "https://raw.githubusercontent.com/metallb/metallb/v0.13.4/config/manifests/metallb-native.yaml"
                  },
                  {
                    "package": "registry.k8s.io/pause",
                    "version": "3.9",
                    "type": "image"
                  }

                ]
              }
            }

**FreeIPA**

    To install FreeIPA, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "freeipa"},

For information on deploying FreeIPA after setting up the cluster, `click here. <../../Roles/Security/index.html>`_

**Jupyterhub**

    To install Jupyterhub, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "jupyter"},

For information on deploying Jupyterhub after setting up the cluster, `click here. <../../InstallingProvisionTool/Platform/InstallJupyterhub.html>`_

**Kserve**

    To install Kserve, do the following:

        * Include the following line under ``softwares`` in ``input/software_config.json``:

            ::

                {"name": "kserve"},

        * Add the following line below the ``softwares`` section:

            ::
                "kserve": [
                    {"name": "istio"},
                    {"name": "cert_manager"},
                    {"name": "knative"}
                    ]

        * A sample format is available `here. </InputParameters.html>`_


For information on deploying Kserve after setting up the cluster, `click here. <../../InstallingProvisionTool/Platform/kserve.html>`_

**Kubeflow**

    To install kubeflow, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "kubeflow"},

For information on deploying kubeflow after setting up the cluster, `click here. <../../InstallingProvisionTool/Platform/kubeflow.html>`_


**Kubernetes**

    To install Kubernetes, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "k8s", "version":"1.26.12"},

    .. note:: The version of the software provided above is the only version of the software Omnia supports.



**OFED**

    To install OFED, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "ofed", "version": "24.01-0.3.3.1"},


    For a list of repositories (and their types) configured for OFED, view the ``input/config/<operating_system>/<operating_system_version>/ofed.json`` file. To customize your OFED installation, update the file.:

    For Ubuntu: ::

            {
                "ofed": {
                  "cluster": [
                    { "package": "ofed",
                      "type": "iso",
                      "url": "https://content.mellanox.com/ofed/MLNX_OFED-24.01-0.3.3.1/MLNX_OFED_LINUX-24.01-0.3.3.1-ubuntu20.04-x86_64.iso",
                      "path": ""
                    }
                  ]
                }
            }


    For RHEL or Rocky: ::

            {
              "ofed": {
                "cluster": [
                  { "package": "ofed",
                    "type": "iso",
                    "url": "https://content.mellanox.com/ofed/MLNX_OFED-24.01-0.3.3.1/MLNX_OFED_LINUX-24.01-0.3.3.1-rhel8.7-x86_64.iso",
                    "path": ""
                  }
                ]
              }
            }

.. note:: If the package version is customized, ensure that the ``version`` value is updated in ``software_config.json``.

**OpenLDAP**

    To install OpenLDAP, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "openldap"},

Features that are part of the OpenLDAP repository are enabled by running `security.yml <../../Roles/Security/index.html>`_

**OpenMPI**

    To install OpenMPI, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "openmpi", "version":"4.1.6"},


OpenMPI is deployed on the cluster when the above configurations are complete and `omnia.yml is run. <../BuildingClusters/index.html>`_

**Pytorch**

    To install PyTorch, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "pytorch"},

            "pytorch": [
                    {"name": "pytorch_cpu"},
                    {"name": "pytorch_amd"},
                    {"name": "pytorch_nvidia"}
                ],

For information on deploying Pytorch after setting up the cluster, `click here. <../../InstallingProvisionTool/Platform/Pytorch.html>`_

**Secure Login Node**

    To secure the login node, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "secure_login_node"},

Features that are part of the secure_login_node repository are enabled by running `security.yml <../../Roles/Security/index.html>`_

**TensorFlow**

    To install TensorFlow, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "tensorflow"},

            "tensorflow": [
                    {"name": "tensorflow_cpu"},
                    {"name": "tensorflow_amd"},
                    {"name": "tensorflow_nvidia"}
                ]

For information on deploying TensorFlow after setting up the cluster, `click here. <../../InstallingProvisionTool/Platform/TensorFlow.html>`_

**Unified Communication X**

    To install UCX, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "ucx", "version":"1.15.0"},

UCX is deployed on the cluster when the ``local_repo.yml`` is run then `omnia.yml is run. <../BuildingClusters/index.html>`_

**vLLM**

    To install vLLM, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "vLLM"},

             "vllm": [
                    {"name": "vllm_amd"},
                    {"name": "vllm_nvidia"}
                ],

For information on deploying vLLM after setting up the cluster, `click here. <../../InstallingProvisionTool/Platform/SetupvLLM.html>`_

**Intel benchmarks**

    To install Intel benchmarks, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "intel_benchmarks", "version": "2024.1.0"},

**AMD benchmarks**

    To install AMD benchmarks, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "amd_benchmarks"},



