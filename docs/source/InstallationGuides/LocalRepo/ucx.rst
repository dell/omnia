Create local Unified Communication X repository
------------------------------------------------

1. Enter the required values in the ``input/software_config.json`` file:

.. csv-table:: Parameters for Software Configuration
   :file: ../../Tables/software_config.csv
   :header-rows: 1
   :keepspace:
   :class: longtable


To install UCX, include the following line under ``softwares```: ::

        {"name": "ucx", "version":"1.15.0"},


For a list of repositories (and their types) configured for UCX, view the ``input/config/<operating_system>/<operating_system_version>/ucx.json`` file. To customize your UCX installation, update the file.

2. Enter the required values in the ``input/local_repo_config.yml`` file. For parameter information, `click here <InputParameters.html>`_.
3. Run the following commands: ::

       cd local_repo
       ansible-playbook local_repo.yml


UCX is deployed on the cluster when the above configurations are complete and `omnia.yml is run. <../BuildingClusters/index.html>`_

