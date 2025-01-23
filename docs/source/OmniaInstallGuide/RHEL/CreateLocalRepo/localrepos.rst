Configuring specific local repositories
-----------------------------------------

**AMD GPU ROCm**

    To install ROCm, do the following:

        * Include the following line under ``softwares`` in ``input/software_config.json``:

            ::

                {"name": "amdgpu", "version": "6.2.2"},

        * Add the following line below the ``softwares`` section:

            ::

                "amdgpu": [
                                {"name": "rocm", "version": "6.2.2" }
                          ]

        * A sample format is available `here. <InputParameters.html>`_

.. note:: If ``amdgpu`` group and ``rocm`` subgroup is provided, the AMD GPU drivers are installed during the cluster provisioning process and the AMD ROCm software stack is installed during ``omnia.yml`` playbook execution.

**CUDA**

    To install CUDA, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "cuda", "version": "12.3.2"},


    For a list of repositories (and their types) configured for CUDA, view the ``input/config/<cluster_os_type>/<cluster_os_version>/cuda.json`` file. To customize your CUDA installation, update the file. URLs for different versions can be found `here <https://developer.nvidia.com/cuda-downloads>`_:

    For RHEL or Rocky Linux: ::

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
    * If the package version is customized, ensure that the ``version`` value is updated in ``software_config.json``.
    * If the target cluster runs on RHEL or Rocky Linux, ensure the "dkms" package is included in ``input/config/<cluster_os_type>/8.x/cuda.json`` as illustrated above.


**OFED**

    To install OFED, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "ofed", "version": "24.01-0.3.3.1"},


    For a list of repositories (and their types) configured for OFED, view the ``input/config/<cluster_os_type>/<cluster_os_version>/ofed.json`` file. To customize your OFED installation, update the file.:

    For RHEL or Rocky Linux: ::

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

**BeeGFS**

    To install BeeGFS, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "beegfs", "version": "7.4.2"},

    For information on deploying BeeGFS after setting up the cluster, `click here <../OmniaCluster/BuildingCluster/Storage/BeeGFS.html>`_.

**NFS**

    To install NFS, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "nfs"},

    For information on deploying NFS after setting up the cluster, `click here <../OmniaCluster/BuildingCluster/Storage/NFS.html>`_.

**Kubernetes**

    To install Kubernetes, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "k8s", "version":"1.29.5"},

    For more information about installing Kubernetes, `click here <../OmniaCluster/BuildingCluster/install_kubernetes.html>`_.

.. note:: The version of the software provided above is the only version of the software Omnia supports.

**Slurm**

    To install Slurm, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "slurm"},

    For more information about installing Kubernetes, `click here <../OmniaCluster/BuildingCluster/install_slurm.html>`_.

.. note:: Omnia recommends to install Slurm with ``always`` and ``partial`` scenarios of ``repo_config`` in ``input/software_config.json``. This is due to intermittent connectivity issues with the EPEL8 repositories.

**FreeIPA**

    To install FreeIPA, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "freeipa"},

    For more information on FreeIPA, `click here <../OmniaCluster/BuildingCluster/Authentication.html#configuring-freeipa-openldap-security>`_.


**OpenLDAP**

    To install OpenLDAP, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "openldap"},

    For more information on OpenLDAP, `click here <../OmniaCluster/BuildingCluster/Authentication.html#configuring-freeipa-openldap-security>`_.


**Secure Login Node**

    To secure the login node, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "secure_login_node"},

    For more information on configuring login node security, `click here <../OmniaCluster/BuildingCluster/Authentication.html#configuring-login-node-security>`_.


**Telemetry**

    To install Telemetry, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "telemetry"},

    For information on deploying Telemetry after setting up the cluster, `click here <../../../Telemetry/index.html>`_.

**PowerScale CSI driver**

    To install PowerScale CSI driver, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "csi_driver_powerscale", "version":"v2.11.0"},

    For information on PowerScale CSI driver, `click here <../AdvancedConfigurationsRHEL/PowerScale_CSI.html>`_.

**Jupyterhub**

    To install Jupyterhub, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "jupyter"},

    For information on deploying Jupyterhub after setting up the cluster, `click here <../InstallAITools/InstallJupyterhub.html>`_.


**Kserve**

    To install Kserve, include the following line under ``softwares`` in ``input/software_config.json``: ::

                {"name": "kserve"},

    For information on deploying Kserve after setting up the cluster, `click here <../InstallAITools/kserve.html>`_.


**Kubeflow**

    To install kubeflow, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "kubeflow"},

    For information on deploying kubeflow after setting up the cluster, `click here <../InstallAITools/kubeflow.html>`_.


**Pytorch**

    To install PyTorch, do the following:

        * Include the following line under ``softwares`` in ``input/software_config.json``:

            ::

                {"name": "pytorch"},

        * Add the following line below the ``softwares`` section:

            ::

                "pytorch": [
                    {"name": "pytorch_cpu"},
                    {"name": "pytorch_amd"},
                    {"name": "pytorch_nvidia"}
                ],

        * A sample format is available `here. <InputParameters.html>`_

For information on deploying Pytorch after setting up the cluster, `click here. <../InstallAITools/Pytorch.html>`_


**TensorFlow**

    To install TensorFlow, do the following:

        * Include the following line under ``softwares`` in ``input/software_config.json``:

            ::

                {"name": "tensorflow"},

        * Add the following line below the ``softwares`` section:

            ::

                "tensorflow": [
                    {"name": "tensorflow_cpu"},
                    {"name": "tensorflow_amd"},
                    {"name": "tensorflow_nvidia"}
                ]

        * A sample format is available `here. <InputParameters.html>`_

For information on deploying TensorFlow after setting up the cluster, `click here <../InstallAITools/TensorFlow.html>`_.


**vLLM**

    To install vLLM, do the following:

        * Include the following line under ``softwares`` in ``input/software_config.json``:

            ::

                {"name": "vLLM"},

        * Add the following line below the ``softwares`` section:

             ::

                "vllm": [
                    {"name": "vllm_amd"},
                    {"name": "vllm_nvidia"}
                ],

        * A sample format is available `here. <InputParameters.html>`_

For information on deploying vLLM after setting up the cluster, `click here <../InstallAITools/vLLM/index.html>`_.


**OpenMPI**

    To install OpenMPI, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "openmpi", "version":"4.1.6"},

OpenMPI is deployed on the cluster when the above configurations are complete and `omnia.yml <../OmniaCluster/BuildingCluster/installscheduler.html>`_ playbook is executed.

For more information on OpenMPI configurations, `click here <../AdvancedConfigurationsRHEL/install_ucx_openmpi.html>`_.

.. note:: The default OpenMPI version for Omnia is 4.1.6. If you change the version in the ``software.json`` file, make sure to update it in the ``openmpi.json`` file in the ``input/config`` directory as well.


**Unified Communication X**

    To install UCX, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "ucx", "version":"1.15.0"},

UCX is deployed on the cluster when ``local_repo.yml`` playbook is executed, followed by the execution of `omnia.yml <../OmniaCluster/BuildingCluster/installscheduler.html>`_.

For more information on UCX configurations, `click here <../AdvancedConfigurationsRHEL/install_ucx_openmpi.html>`_.


**Intel benchmarks**

    To install Intel benchmarks, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "intel_benchmarks", "version": "2024.1.0"},

For more information on Intel benchmarks, `click here <../AdvancedConfigurationsRHEL/AutomatingOneAPI.html>`_.


**AMD benchmarks**

    To install AMD benchmarks, include the following line under ``softwares`` in ``input/software_config.json``: ::

            {"name": "amd_benchmarks"},

For more information on AMD benchmarks, `click here <../AdvancedConfigurationsRHEL/AutomatingOpenMPI.html>`_.


**Custom repositories**

    Include the following line under ``softwares`` in ``input/software_config.json``: ::

                {"name": "custom"},

    Create a ``custom.json`` file in the following directory: ``input/config/<cluster_os_type>/<cluster_os_version>`` to define the repositories. For example, For a cluster running RHEL 8.8, go to ``input/config/rhel/8.8/`` and create the file there. The file is a JSON list consisting of the package name, repository type, URL (optional), and version (optional). Below is a sample version of the file: ::

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

