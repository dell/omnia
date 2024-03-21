Create local OpenMPI repository
--------------------------------

1. Enter the required values in the ``input/software_config.json`` file:

.. csv-table:: Parameters for Software Configuration
   :file: ../../Tables/software_config.csv
   :header-rows: 1
   :keepspace:
   :class: longtable


To install UCX, include the following line under ``softwares```: ::

        {"name": "openmpi", "version":"4.1.6"},


For a list of repositories (and their types) configured for OpenMPI, view the ``input/config/<operating_system>/<operating_system_version>/openmpi.json`` file. To customize your OpenMPI installation, update the file.

2. Enter the required values in the ``input/local_repo_config.yml`` file. For parameter information, `click here <InputParameters.html>`_.
3. Run the following commands: ::

       cd local_repo
       ansible-playbook local_repo.yml


OpenMPI is deployed on the cluster when the above configurations are complete and `omnia.yml is run. <../BuildingClusters/index.html>`_

