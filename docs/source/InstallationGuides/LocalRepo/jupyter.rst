Create local kubeflow repository
-------------------------------

1. Enter the required values in the ``input/software_config.json`` file:

.. csv-table:: Parameters for Software Configuration
   :file: ../../Tables/software_config.csv
   :header-rows: 1
   :keepspace:
   :class: longtable


To install kubeflow, include the following line under ``softwares```: ::

        {"name": "kubeflow"},


For a list of repositories (and their types) configured for kubeflow, view the ``input/config/<operating_system>/<operating_system_version>/kubeflow.json`` file. To customize your kubeflow installation, update the file.

2. Enter the required values in the ``input/local_repo_config.yml`` file. For parameter information, `click here <InputParameters.html>`_.
3. Run the following commands: ::

       cd local_repo
       ansible-playbook local_repo.yml


For information on deploying kubeflow after setting up the cluster, `click here. <../../Roles/Platform/kubeflow.html>`_

