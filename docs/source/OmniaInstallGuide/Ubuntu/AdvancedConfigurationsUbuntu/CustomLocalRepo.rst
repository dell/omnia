Configuring custom repositories
-------------------------------

Use the local repository feature to create a customized set of local repositories on the control plane for the cluster nodes to access.

1. Ensure the ``custom`` entry is included in the ``software_config.json`` file. ::

    {
        "cluster_os_type": "ubuntu",
        "cluster_os_version": "22.04",
        "repo_config": "partial",
        "softwares": [
            {"name": "amdgpu", "version": "6.2.2"},
            {"name": "cuda", "version": "12.3.2"},
            {"name": "bcm_roce", "version": "230.2.54.0"},
            {"name": "ofed", "version": "24.01-0.3.3.1"},
            {"name": "openldap"},
            {"name": "secure_login_node"},
            {"name": "nfs"},
            {"name": "beegfs", "version": "7.4.2"},
            {"name": "k8s", "version":"1.29.5"},
            {"name": "roce_plugin"},
            {"name": "jupyter"},
            {"name": "kubeflow"},
            {"name": "kserve"},
            {"name": "pytorch"},
            {"name": "tensorflow"},
            {"name": "vllm"},
            {"name": "telemetry"},
            {"name": "ucx", "version": "1.15.0"},
            {"name": "openmpi", "version": "4.1.6"},
            {"name": "intelgaudi", "version": "1.19.1-26"},
            {"name": "csi_driver_powerscale", "version":"v2.11.0"}
        ],
        "bcm_roce": [
            {"name": "bcm_roce_libraries", "version": "230.2.54.0"}
        ],
        "amdgpu": [
            {"name": "rocm", "version": "6.2.2" }
        ],
        "intelgaudi": [
            {"name": "intel"}
        ],
        "vllm": [
            {"name": "vllm_amd"},
            {"name": "vllm_nvidia"}
        ],
        "pytorch": [
            {"name": "pytorch_cpu"},
            {"name": "pytorch_amd"},
            {"name": "pytorch_nvidia"},
            {"name": "pytorch_gaudi"}
        ],
        "tensorflow": [
            {"name": "tensorflow_cpu"},
            {"name": "tensorflow_amd"},
            {"name": "tensorflow_nvidia"}
        ]
    }

.. note:: For Rocky Linux OS, the ``cluster_os_type`` in the above sample will be ``rocky``.

2. Create a ``custom.json`` file in the following directory: ``input/config/<cluster_os_type>/<cluster_os_version>`` to define the repositories. For example, For a cluster running RHEL 8.8, go to ``input/config/rhel/8.8/`` and create the file there. The file is a JSON list consisting of the package name, repository type, URL (optional), and version (optional). Below is a sample version of the file: ::

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

2. Enter the parameters required in ``input/local_repo_config.yml`` as explained `here <../CreateLocalRepo/InputParameters.html#id2>`_.

3. Run the following commands: ::

    cd local_repo
    ansible-playbook local_repo.yml

