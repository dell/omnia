Configuring custom repositories
-------------------------------

Use the local repository feature to create a customized set of local repositories on the control plane for the cluster nodes to access.

1. Ensure the ``custom`` entry is included in the ``software_config.json`` file. ::

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
            {"name": "tensorflow"}
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

2. Create a ``custom.json`` file in the following directory: ``input/config/<operating_system>/<operating_system_version>`` to define the repositories. For example, For a cluster running RHEL 8.8, go to ``input/config/rhel/8.8/`` and create the file there. The file is a JSON list consisting of the package name, repository type, URL (optional), and version (optional). Below is a sample version of the file: ::

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

2. Enter the parameters required in ``input/local_repo_config.yml`` as explained `here <RunningLocalRepo.html>`_.

3. Run the following commands: ::

    cd local_repo
    ansible-playbook local_repo.yml

