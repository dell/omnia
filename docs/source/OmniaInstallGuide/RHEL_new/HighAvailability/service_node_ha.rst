High Availability (HA) for the Service Node
=====================================================

In a large HPC cluster deployed by Omnia, service nodes are used to balance the load on the OIM. Each service node is responsible for discovering and provisioning a set of compute nodes. 
For such scenarios, in order to maintain uninterrupted cluster experience, Omnia provides an option to enable high availability for the service nodes. Omnia achieves this in the form of Active/Passive service nodes - provides a fully redundant 
instance of the service nodes, which is only brought online when its associated primary node fails.

Prerequisites
--------------

* Ensure that the passive service nodes have ``service_node`` role assigned to them in the ``/opt/omnia/input/project_default/roles_config.yml`` input file. For more information, `click here <../composable_roles.html>`_.

* Ensure that all the service nodes (active/passive) are connected to the Internet.

* Ensure that the ``local_repo.yml`` playbook has been run successfully at least once. Before running it, verify that the ``opt/omnia/input/project_default/software_config.json`` file contains ``{"name": "service_node"}`` in the ``softwares`` list.

* To enable and configure the HA for Service nodes, fill up the necessary parameters in the ``high_availability_config.yml`` config file present in the ``/opt/omnia/input/project_default/`` directory. Once the config file is updated, run the ``prepare_oim.yml`` playbook.

    .. csv-table:: Parameters for Service Node HA
        :file: ../../../Tables/sn_ha.csv
        :header-rows: 1
        :keepspace:

.. note:: 
  
    * Once the ``prepare_oim.yml`` playbook has been executed, any subsequent edits to the ``high_availability_config.yml`` or ``roles_config.yml`` files will not take effect. To apply changes made to these configuration files, you must re-run the ``prepare_oim.yml`` playbook.
    * The virtual IP addresses specified in the ``high_availability_config.yml`` file must be within the same subnet as the admin network.

Playbook execution
-------------------

Once the details have been provided to the input files and the ``prepare_oim.yml`` playbook is executed, passive service nodes can be discovered during the cluster discovery and provision process using the below command:

::

    ansible-playbook discovery_provision.yml --tags "management_layer"

.. note:: Ensure that ``local_repo.yml`` playbook has been executed successfully before provisioning.

Sample
-------

::

    service_node_ha: 
        enable_service_ha: false 
        service_nodes: 
         	
          - virtual_ip_address: “10.5.0.11” 
            active_node_service_tag: “ABC123” 
              passive_nodes:  
                - node_service_tags: [“DEF456”]

          - virtual_ip_address: “10.5.0.12” 
            active_node_service_tag: “GHI789” 
              passive_nodes:  
                - node_service_tags: [“JKL012”]