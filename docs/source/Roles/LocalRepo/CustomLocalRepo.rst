Configuring custom repositories
-------------------------------

Use the local repository feature to create a customized set of local repositories on the control plane for the cluster nodes to access.

1. Ensure the ``custom`` entry is included in the ``software_config.json`` file. ::

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

2. Enter the parameters required in ``input/local_repo_config.yml`` as explained `here <index.html>`_.

3. Run the following commands: ::

    cd local_repo
    ansible-playbook local_repo.yml

