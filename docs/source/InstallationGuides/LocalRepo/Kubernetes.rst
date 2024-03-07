Create local Kubernetes repository
----------------------------------

1. Enter the required values in the ``input/software_config.json`` file:

.. csv-table:: Parameters for Software Configuration
   :file: ../../Tables/software_config.csv
   :header-rows: 1
   :keepspace:
   :class: longtable


To install Kubernetes, include the following line under ``softwares```: ::

        {"name": "k8s", "version":"1.26.12"},
        
.. note:: The version of the software provided above is the only version of the software Omnia supports. 

2. Enter the required values in the ``input/local_repo_config.yml`` file. For parameter information, `click here <RunningLocalRepo.html>`_.
3. Run the following commands: ::

       cd local_repo
       ansible-playbook local_repo.yml

To complete the installation of Kubernetes on the cluster, `click here. <../BuildingClusters/index.rst>`_