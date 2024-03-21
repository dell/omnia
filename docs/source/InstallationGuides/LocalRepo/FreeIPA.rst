Create FreeIPA repository
-------------------------

1. Enter the required values in the ``input/software_config.json`` file:

.. csv-table:: Parameters for Software Configuration
   :file: ../../Tables/software_config.csv
   :header-rows: 1
   :keepspace:
   :class: longtable


To install FreeIPA, include the following line under ``softwares```: ::

        {"name": "freeipa"},


For a list of repositories (and their types) configured for FreeIPA, view the ``input/config/<operating_system>/<operating_system_version>/freeipa.json`` file. To customize your FreeIPA installation, update the file.:

2. Enter the required values in the ``input/local_repo_config.yml`` file. For parameter information, `click here <InputParameters.html>`_.
3. Run the following commands: ::

       cd local_repo
       ansible-playbook local_repo.yml
