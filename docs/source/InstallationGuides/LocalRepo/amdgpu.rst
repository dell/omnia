Create local ROCm repository
-----------------------------

1. Enter the required values in the ``input/software_config.json`` file:

.. csv-table:: Parameters for Software Configuration
   :file: ../../Tables/software_config.csv
   :header-rows: 1
   :keepspace:
   :class: longtable


To install ROCm, include the following line under ``softwares```: ::

         "amdgpu": [
                {"name": "rocm", "version": "6.0" }
            ]


2. Enter the required values in the ``input/local_repo_config.yml`` file. For parameter information, `click here <RunningLocalRepo.html>`_.
3. Run the following commands: ::

       cd local_repo
       ansible-playbook local_repo.yml