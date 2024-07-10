Input parameters for Local Repositories
----------------------------------------

* Input all required values in ``input/software_config.json``.

.. csv-table:: Parameters for Software Configuration
   :file: ../../Tables/software_config.csv
   :header-rows: 1
   :keepspace:
   :class: longtable

Sample version of the file:

* For Ubuntu:

    ::

        {
            "cluster_os_type": "ubuntu",
            "cluster_os_version": "22.04",
            "repo_config": "partial",
            "softwares": [
                {"name": "amdgpu", "version": "6.0"},
                {"name": "cuda", "version": "12.3.2"},
                {"name": "bcm_roce", "version": "229.2.61.0"},
                {"name": "ofed", "version": "24.01-0.3.3.1"},
                {"name": "openldap"},
                {"name": "secure_login_node"},
                {"name": "nfs"},
                {"name": "beegfs", "version": "7.4.2"},
                {"name": "k8s", "version":"1.26.12"},
                {"name": "roce_plugin"},
                {"name": "jupyter"},
                {"name": "kubeflow"},
                {"name": "kserve"},
                {"name": "pytorch"},
                {"name": "tensorflow"},
                {"name": "vllm"},
                {"name": "telemetry"},
                {"name": "ucx", "version": "1.15.0"},
                {"name": "openmpi", "version": "4.1.6"}
            ],

            "bcm_roce": [
                {"name": "bcm_roce_libraries", "version": "229.2.61.0"}
            ],
            "amdgpu": [
                {"name": "rocm", "version": "6.0" }
            ],
            "vllm": [
                {"name": "vllm_amd"},
                {"name": "vllm_nvidia"}
            ],
            "pytorch": [
                {"name": "pytorch_cpu"},
                {"name": "pytorch_amd"},
                {"name": "pytorch_nvidia"}
            ],
            "tensorflow": [
                {"name": "tensorflow_cpu"},
                {"name": "tensorflow_amd"},
                {"name": "tensorflow_nvidia"}
            ]
        }

* For RHEL/Rocky Linux OS:

.. note:: For Rocky Linux OS, the ``cluster_os_type`` in the below sample will be ``rocky``.

::

        {
            "cluster_os_type": "rhel",
            "cluster_os_version": "8.8",
            "repo_config": "partial",
            "softwares": [
                {"name": "amdgpu", "version": "6.0"},
                {"name": "cuda", "version": "12.3.2"},
                {"name": "ofed", "version": "24.01-0.3.3.1"},
                {"name": "freeipa"},
                {"name": "openldap"},
                {"name": "secure_login_node"},
                {"name": "nfs"},
                {"name": "beegfs", "version": "7.4.2"},
                {"name": "slurm"},
                {"name": "k8s", "version":"1.26.12"},
                {"name": "jupyter"},
                {"name": "kubeflow"},
                {"name": "kserve"},
                {"name": "pytorch"},
                {"name": "tensorflow"},
                {"name": "vllm"},
                {"name": "telemetry"},
                {"name": "intel_benchmarks", "version": "2024.1.0"},
                {"name": "amd_benchmarks"},
                {"name": "utils"},
                {"name": "ucx", "version": "1.15.0"},
                {"name": "openmpi", "version": "4.1.6"}
            ],

            "amdgpu": [
                {"name": "rocm", "version": "6.0" }
            ],
            "vllm": [
                {"name": "vllm_amd"},
                {"name": "vllm_nvidia"}
            ],
            "pytorch": [
                {"name": "pytorch_cpu"},
                {"name": "pytorch_amd"},
                {"name": "pytorch_nvidia"}
            ],
            "tensorflow": [
                {"name": "tensorflow_cpu"},
                {"name": "tensorflow_amd"},
                {"name": "tensorflow_nvidia"}
            ]

        }


For a list of accepted values in ``softwares``, go to ``input/config/<cluster_os_type>/<cluster_os_version>`` and view the list of JSON files available. The filenames present in this location (without the * .json extension) are a list of accepted software names. The repositories to be downloaded for each software are listed the corresponding JSON file. For example, for a cluster running Ubuntu 22.04, go to ``input/config/ubuntu/22.04/`` and view the file list:

::

    amdgpu.json
    bcm_roce.json
    beegfs.json
    cuda.json
    jupyter.json
    k8s.json
    kserve.json
    kubeflow.json
    roce_plugin.json
    nfs.json
    ofed.json
    openldap.json
    pytorch.json
    tensorflow.json
    vllm.json

For a list of repositories (and their types) configured for AMD GPUs, view the ``amdgpu.json`` file: ::

    {
      "amdgpu": {
        "cluster": [
            {"package": "linux-headers-$(uname -r)", "type": "deb", "repo_name": "jammy"},
            {"package": "linux-modules-extra-$(uname -r)", "type": "deb", "repo_name": "jammy"},
            {"package": "amdgpu-dkms", "type": "deb", "repo_name": "amdgpu"}
        ]
      },
      "rocm": {
        "cluster": [
          {"package": "rocm-hip-sdk{{ rocm_version }}*", "type": "deb", "repo_name": "rocm"}
        ]
      }
    }

.. note:: To configure a locally available repository that does not have a pre-defined json file, `click here <CustomLocalRepo.html>`_.

* Input the required values in ``input/local_repo_config.yml``.

.. csv-table:: Parameters for Local Repository Configuration
   :file: ../../Tables/local_repo_config.csv
   :header-rows: 1
   :widths: auto

* Input ``docker_username`` and ``docker_password`` in ``input/provision_config_credentials.yml``  to avoid image pullback errors.