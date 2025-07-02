Step 2: Composable roles in Omnia
==================================

In Omnia, nodes are organized based on their assigned roles. Nodes with the same role can be clubbed under a group. By combining both roles and groups, Omnia offers a powerful and flexible approach to managing large-scale node infrastructures, ensuring both logical organization and physical optimization of resources.

* **Role**: A role defines what a node does in the system. It is a way to categorize nodes based on their functionality. For example, a node could have the role of a Login server, a Compiler, a K8Worker (Kubernetes Worker), or a SLURMWorker (a node in a slurm job scheduler system). Roles help group nodes that perform similar tasks, making it easier to manage and assign resources.

* **Group**: A group is based on the physical characteristics of the nodes. It refers to nodes that are located in the same place or have similar hardware. For example, nodes in the same rack or SU (Scalable Unit) might be grouped together, with specific roles like HeadNode or ServiceNode. Groups help with physical organization and management of nodes.

Roles offered by Omnia
-------------------------

.. note:: 
    
    * Nested roles and groups are not supported.
    * Maximum number of supported roles are 100.
    * At least one role is mandatory, and you must not change the name of the roles.
    * The roles are case-sensitive in nature.
    * Groups assigned to the **Management** layer roles should not be assigned to **Compute** layer roles.
    * Omnia also supports HA functionality for the ``OIM`` and the ``service_node``. For more information, `click here <HighAvailability/index.html>`_.

.. csv-table:: Types of Roles
   :file: ../../Tables/omnia_roles.csv
   :header-rows: 1
   :keepspace:

Group attributes
----------------

Nodes with similar roles or functionalities can be grouped together. To do so, fill up the ``roles_config.yml`` input file in the ``/opt/omnia/input/project_default`` directory which includes all necessary attributes for the nodes, based on their role within the cluster. Each group will have following attributes as indicated in the table below:

.. note:: Groups associated with the ``service_node`` and ``oim_ha_node`` role should not be used to fulfill any other roles.

.. csv-table:: Group attributes
   :file: ../../Tables/group_attributes.csv
   :header-rows: 1
   :keepspace:
   
Sample
-------

Here's a sample (using mapping file) for your reference:

.. note:: 
    
    * If you want to use BMC discovery mechanism, ensure to provide the value for BMC ``static_range``.
    * If you want to use switch-based discovery, ensure to provide the switch ``ip`` and ``port`` along with the BMC details.


::
    
    Groups:
        grp0:
            location_id: SU-1.RACK-1
            resource_mgr_id: ""
            parent: ""
            bmc_details:
                static_range: ""
            switch_details:
                ip: ""
                ports: ""
            architecture: "x86"

        grp1:
            location_id: SU-1.RACK-2
            resource_mgr_id: ""
            parent: ""
            bmc_details:
                static_range: ""
            switch_details:
                ip: ""
                ports: ""
            architecture: "x86"

    Roles:
        - name: "default"
          groups:
            - grp0

        - name: "service_node"
          groups:
            - grp1


