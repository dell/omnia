Local repositories for the  cluster
=====================================

The local repository feature will help create offline repositories on control plane which all the cluster  nodes will access. ``local_repo/local_repo.yml`` runs with inputs from ``input/software_config.json`` and ``input/local_repo_config.yml``:

1. Enter the required values in the ``input/software_config.json`` file:

.. csv-table:: Parameters for Software Configuration
   :file: ../../Tables/software_config.csv
   :header-rows: 1
   :keepspace:

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

.. csv-table:: Parameters for Local Repositories
   :file: ../../Tables/local_repo_config.csv
   :header-rows: 1
   :keepspace:


Alternatively, run the following commands: ::

    cd local_repo
    ansible-playbook local_repo.yml



