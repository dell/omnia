Create local TensorFlow repository
-----------------------------------

1. Enter the required values in the ``input/software_config.json`` file:

.. csv-table:: Parameters for Software Configuration
   :file: ../../Tables/software_config.csv
   :header-rows: 1
   :keepspace:
   :class: longtable


To install TensorFlow, include the following line under ``softwares```: ::

        {"name": "tensorflow"},

        "tensorflow": [
                {"name": "tensorflow_cpu"},
                {"name": "tensorflow_amd"},
                {"name": "tensorflow_nvidia"}
            ]


For a list of repositories (and their types) configured for TensorFlow, view the ``input/config/<operating_system>/<operating_system_version>/tensorflow.json`` file. To customize your TensorFlow installation, update the file.

2. Enter the required values in the ``input/local_repo_config.yml`` file. For parameter information, `click here <RunningLocalRepo.html>`_.
3. Run the following commands: ::

       cd local_repo
       ansible-playbook local_repo.yml

For information on deploying TensorFlow after setting up the cluster, `click here. <../../Roles/Platform/TensorFlow.html>`_

