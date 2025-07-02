Input parameters for Local Repositories
==========================================

The ``local_repo.yml`` playbook is dependent on the inputs provided to the following input files:

* ``/opt/omnia/input/project_default/software_config.json``
* ``/opt/omnia/input/project_default/local_repo_config.yml``

``/opt/omnia/input/project_default/software_config.json``
----------------------------------------------------------

Based on the inputs provided to the ``/opt/omnia/input/project_default/software_config.json``, the software packages/images are accessed from the Pulp container and the desired software stack is deployed on the cluster nodes.

.. csv-table:: Parameters for Software Configuration
   :file: ../../../Tables/software_config_rhel.csv
   :header-rows: 1
   :keepspace:
   :widths: auto

Here's a sample of the ``software_config.json`` for RHEL clusters:

::

    {
        "cluster_os_type": "rhel",
        "cluster_os_version": "9.6",
        "iso_file_path": "",
        "repo_config": "always",
        "softwares": [
            {"name": "amdgpu", "version": "6.3.1"},
            {"name": "cuda", "version": "12.8.0"},
            {"name": "ofed", "version": "24.10-1.1.4.0"},
            {"name": "service_node" },
            {"name": "openldap"},
            {"name": "nfs"},
            {"name": "k8s", "version":"1.31.4"},
            {"name": "slurm"}
        ],
        "amdgpu": [
            {"name": "rocm", "version": "6.3.1" }
        ],
        "slurm": [
            {"name": "slurm_control_node"},
            {"name": "slurm_node"},
            {"name": "login"}
        ]
    }

.. note::

    * For a list of accepted ``softwares``, go to the ``/opt/omnia/input/project_default/config/<cluster_os_type>/<cluster_os_version>`` and view the list of JSON files available. The filenames present in this location are the list of accepted softwares. For example, for a cluster running RHEL 9.6, go to ``/opt/omnia/input/project_default/config/rhel/9.6/`` and view the file list for accepted softwares.
    * Omnia supports a single version of any software packages in the ``software_config.json`` file. Ensure that multiple versions of the same package is not mentioned.
    * For software packages that do not have a pre-defined json file in ``/opt/omnia/input/project_default/config/<cluster_os_type>/<cluster_os_version>``, you need to create a ``custom.json`` file with the package details. For more information, `click here <../../AdvancedConfigurations/CustomLocalRepo.html>`_.

``/opt/omnia/input/project_default/local_repo_config.yml``
-----------------------------------------------------------

.. csv-table:: Parameters for Local Repository Configuration
   :file: ../../../Tables/local_repo_config_rhel.csv
   :header-rows: 1
   :keepspace:
   :widths: auto