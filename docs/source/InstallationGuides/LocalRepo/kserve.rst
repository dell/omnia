Create local Kserve repository
------------------------------

1. Enter the required values in the ``input/software_config.json`` file:

.. csv-table:: Parameters for Software Configuration
   :file: ../../Tables/software_config.csv
   :header-rows: 1
   :keepspace:
   :class: longtable


To install Kserve, include the following line under ``softwares```: ::

         "kserve": [
                {"name": "istio"},
                {"name": "cert_manager"},
                {"name": "knative"}
            ]


For a list of repositories (and their types) configured for Kserve, view the ``input/config/<operating_system>/<operating_system_version>/kserve.json`` file. To customize your Kserve installation, update the file.

2. Enter the required values in the ``input/local_repo_config.yml`` file. For parameter information, `click here <RunningLocalRepo.html>`_.
3. Run the following commands: ::

       cd local_repo
       ansible-playbook local_repo.yml

For information on deploying Kserve after setting up the cluster, `click here. <../../Roles/Platform/kserve.html>`_
