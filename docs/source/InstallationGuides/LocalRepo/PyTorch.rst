Create local PyTorch repository
-------------------------------

1. Enter the required values in the ``input/software_config.json`` file:

.. csv-table:: Parameters for Software Configuration
   :file: ../../Tables/software_config.csv
   :header-rows: 1
   :keepspace:
   :class: longtable


To install PyTorch, include the following line under ``softwares```: ::

        {"name": "pytorch"},


For a list of repositories (and their types) configured for PyTorch, view the ``input/config/<operating_system>/<operating_system_version>/pytorch.json`` file. To customize your PyTorch installation, update the file.

2. Enter the required values in the ``input/local_repo_config.yml`` file. For parameter information, `click here <RunningLocalRepo.html>`_.
3. Run the following commands: ::

       cd local_repo
       ansible-playbook local_repo.yml


For information on deploying PyTorch after setting up the cluster, `click here. <../../Roles/Platform/Pytorch.html>`_

