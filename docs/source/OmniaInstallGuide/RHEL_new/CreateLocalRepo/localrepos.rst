Configuring specific local repositories
-----------------------------------------

**AMD GPU ROCm**

    To install ROCm, do the following:

        * Include the following line under ``softwares`` in ``software_config.json``:

            ::

                {"name": "amdgpu", "version": "6.3.1"},

        * Add the following line below the ``softwares`` section:

            ::

                "amdgpu": [
                                {"name": "rocm", "version": "6.3.1" }
                          ]

        * A sample format is available `here. <InputParameters.html>`_

.. note:: If ``amdgpu`` group and ``rocm`` subgroup is provided, the AMD GPU drivers are installed during the cluster provisioning process and the AMD ROCm software stack is installed during ``omnia.yml`` playbook execution.

**CUDA**

    To install CUDA, include the following line under ``softwares`` in ``software_config.json``: ::

            {"name": "cuda", "version": "12.8.0"},

    For a list of repositories (and their types) configured for CUDA, view the ``/opt/omnia/input/project_default/config/<cluster_os_type>/<cluster_os_version>/cuda.json`` file. To customize your CUDA installation, update the ``url`` parameter with your desired CUDA version URL. URLs for different versions can be found `here <https://developer.nvidia.com/cuda-downloads>`_. ::

        {
          "cuda": {
            "cluster": [
              { "package": "cuda",
                "type": "iso",
                "url": "https://developer.download.nvidia.com/compute/cuda/12.8.0/local_installers/cuda-repo-rhel9-12-8-local-12.8.0_570.86.10-1.x86_64.rpm",
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
    * If the package version is customized, ensure that the same ``version`` value is also updated in the ``software_config.json``.
    * If the target cluster runs on RHEL, ensure that the "dkms" package is also included in ``/opt/omnia/input/project_default/config/<cluster_os_type>/9.x/cuda.json``, as shown above.

**OFED**

    To install OFED, include the following line under ``softwares`` in ``software_config.json``: ::

            {"name": "ofed", "version": "24.01-0.3.3.1"},

    For a list of repositories (and their types) configured for OFED, view the ``/opt/omnia/input/project_default/config/<cluster_os_type>/<cluster_os_version>/ofed.json`` file. To customize your OFED installation, update the ``url`` parameter with your desired OFED version URL. ::

        {
          "ofed": {
            "cluster": [
              { "package": "ofed",
                "type": "iso",
                "url": "https://content.mellanox.com/ofed/MLNX_OFED-24.01-0.3.3.1/MLNX_OFED_LINUX-24.01-0.3.3.1-rhel9.0-x86_64.iso",
                "path": ""
              }
            ]
          }
        }

.. note:: If the package version is customized, ensure that the same ``version`` value is also updated in the ``software_config.json``.

**BeeGFS**

    To install BeeGFS, include the following line under ``softwares`` in ``software_config.json``: ::

            {"name": "beegfs", "version": "7.4.5"},

    For information on deploying BeeGFS after setting up the cluster, `click here <../OmniaCluster/BuildingCluster/Storage/BeeGFS.html>`_.

**NFS**

    To install NFS, include the following line under ``softwares`` in ``software_config.json``: ::

            {"name": "nfs"},

    For information on deploying NFS after setting up the cluster, `click here <../OmniaCluster/BuildingCluster/Storage/NFS.html>`_.

**Kubernetes**

    To install Kubernetes, include the following line under ``softwares`` in ``software_config.json``: ::

            {"name": "k8s", "version":"1.31.4"},

    For more information about installing Kubernetes, `click here <../OmniaCluster/BuildingCluster/install_kubernetes.html>`_.

.. note:: The version of ``k8s`` provided above is the only version of the package that Omnia supports.

**Slurm**

    To install Slurm, include the following line under ``softwares`` in ``software_config.json``: ::

            {"name": "slurm"},

    For more information about installing Slurm, `click here <../OmniaCluster/BuildingCluster/install_slurm.html>`_.

.. note:: Omnia recommends to install Slurm with ``repo_config`` variable set to ``always``  in ``software_config.json``. This is due to intermittent connectivity issues with the EPEL8 repositories.

**FreeIPA**

    To install FreeIPA, include the following line under ``softwares`` in ``software_config.json``: ::

            {"name": "freeipa"},

    For more information on FreeIPA, `click here <../OmniaCluster/BuildingCluster/Authentication.html#configuring-freeipa-openldap-security>`_.


**OpenLDAP**

    To install OpenLDAP, include the following line under ``softwares`` in ``software_config.json``: ::

            {"name": "openldap"},

    For more information on OpenLDAP, `click here <../OmniaCluster/BuildingCluster/Authentication.html#configuring-freeipa-openldap-security>`_.


**OpenMPI**

    To install OpenMPI, include the following line under ``softwares`` in ``software_config.json``: ::

            {"name": "openmpi", "version":"4.1.6"},

    OpenMPI is deployed on the cluster when the above configurations are complete and `omnia.yml <../OmniaCluster/BuildingCluster/installscheduler.html>`_ playbook is executed.

    For more information on OpenMPI configurations, `click here <../../AdvancedConfigurations/install_ucx_openmpi.html>`_.

.. note:: The default OpenMPI version for Omnia is 4.1.6. If you change the version in the ``software_config.json`` file, make sure to update it in the ``openmpi.json`` file in the ``config`` directory as well.


**Unified Communication X**

    To install UCX, include the following line under ``softwares`` in ``software_config.json``: ::

            {"name": "ucx", "version":"1.15.0"},

    UCX is deployed on the cluster when ``local_repo.yml`` playbook is executed, followed by the execution of `omnia.yml <../OmniaCluster/BuildingCluster/installscheduler.html>`_.

    For more information on UCX configurations, `click here <../../AdvancedConfigurations/install_ucx_openmpi.html>`_.


**Intel benchmarks**

    To install Intel benchmarks, include the following line under ``softwares`` in ``software_config.json``: ::

            {"name": "intel_benchmarks", "version": "2024.1.0"},

    For more information on Intel benchmarks, `click here <../../AdvancedConfigurations/AutomatingOneAPI.html>`_.


**AMD benchmarks**

    To install AMD benchmarks, include the following line under ``softwares`` in ``software_config.json``: ::

            {"name": "amd_benchmarks"},

    For more information on AMD benchmarks, `click here <../../AdvancedConfigurations/AutomatingOpenMPI.html>`_.

**Racadm**

    To install Racadm, include the following line under ``softwares`` in ``software_config.json``: ::

            {"name": "racadm"},

    A sample format is available `here. <InputParameters.html>`_

**Custom packages**

    Include the following line under ``softwares`` in ``software_config.json``: ::

                {"name": "additional_software"},

    Create a ``additional_software.json`` file in the following directory: ``/opt/omnia/input/project_default/config/<cluster_os_type>/<cluster_os_version>`` and add your choice of additional software. For example, For a cluster running RHEL 9.6, go to ``/opt/omnia/input/project_default/config/rhel/9.6/`` and create the file there. For more information, `click here <../../../Utils/software_update.html>`_.
