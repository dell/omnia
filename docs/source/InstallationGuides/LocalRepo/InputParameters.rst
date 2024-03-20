Input parameters for Local Repositories
----------------------------------------

* Input all required values in ``input/software_config.json``.

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
                {"name": "jupyter"},
                {"name": "openldap"},
                {"name": "kubeflow"},
                {"name": "beegfs", "version": "7.4.2"},
                {"name": "nfs"},
                {"name": "kserve"},
                {"name": "amdgpu", "version": "6.0"},
                {"name": "cuda", "version": "12.3.2"},
                {"name": "ofed", "version": "24.01-0.3.3.1"},
                {"name": "vllm"},
                {"name": "pytorch"},
                {"name": "tensorflow"},
                {"name": "bcm_roce", "version": "229.2.9.0"}
            ],

            "kserve": [
                {"name": "istio"},
                {"name": "cert_manager"},
                {"name": "knative"}
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

For a list of accepted values in ``softwares``, go to ``input/config/<operating_system>/<operating_system_version>`` and view the list of JSON files available. The filenames present in this location (without the * .json extension) are a list of accepted software names. The repositories to be downloaded for each software are listed the corresponding JSON file. For example: For a cluster running Ubuntu 22.04, go to ``input/config/ubuntu/22.04/`` and view the file list:

::

    amdgpu.json
    bcm_roce.json
    beegfs.json
    cuda.json
    jupyter.json
    k8s.json
    kserve.json
    kubeflow.json
    nfs.json
    ofed.json
    openldap.json
    pytorch.json
    tensorflow.json
    vllm.json

For a list of repositories (and their types) configured for amdgpu, view the ``amdgpu.json``` file: ::

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