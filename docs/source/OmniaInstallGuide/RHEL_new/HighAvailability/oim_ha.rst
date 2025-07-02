High Availability (HA) for the OIM
============================================

The Omnia Infrastructure Manager (OIM) is the most critical node of the High-Performance Computing (HPC) cluster set up by Omnia. It's
responsible for the overall creation and maintenance of the cluster, performing tasks such as node discovery and provision, telemetry
monitoring and much more. So, enabling HA for the OIM is essential to maintain a smooth and uninterrupted cluster experience.

What is HA?
------------

High Availability (HA) refers to crucial systems that need to be operational for long periods of time with minimal downtime. This ensures that the services or functionalities
are always available, even when a critical component of ths system fails. Omnia achieves this in the form of Active/Passive OIM nodes - provides a fully redundant 
instance of the OIM nodes, which is only brought online when its associated primary node fails. Omnia uses Pacemaker and CoroSync (PCS) containers along with a Virtual IP address
to create the OIM HA. The ``prepare_oim.yml`` playbook sets up the ``omnia_pcs`` container which handles the HA functionality.

Prerequisites
--------------

* Ensure that the passive OIM nodes have ``oim_ha_node`` role assigned to them in the ``/opt/omnia/input/project_default/roles_config.yml`` input file. For more information, `click here <../composable_roles.html>`_.

* Ensure that the passive OIM node has two dedicated NICs. One of them is used to connect to the Internet whereas the other one is used to communicate internally within the cluster.

* For enabling HA functionality on the OIM, ensure that the Omnia shared path is set to an external NFS server.

* To enable and configure HA for OIM, fill up the necessary parameters in the ``high_availability_config.yml`` config file present in the ``/opt/omnia/input/project_default/`` directory. Once the config file is updated, run the ``prepare_oim.yml`` playbook.

    .. csv-table:: Parameters for OIM HA
        :file: ../../../Tables/oim_ha.csv
        :header-rows: 1
        :keepspace:

.. note:: The virtual IP addresses specified in the ``high_availability_config.yml`` file must be within the same subnet as the admin network.

Playbook execution
--------------------

Once the details have been provided to the input files and the ``prepare_oim.yml`` playbook is executed, passive OIM nodes can be discovered during the cluster discovery and provision process.

::

    ansible-playbook discovery_provision.yml --tags "management_layer"

.. note:: Ensure that ``local_repo.yml`` playbook has been executed successfully before provisioning.

Sample
-------

::

    oim_ha:
        enable_oim_ha: false
        admin_virtual_ip_address: ""
        bmc_virtual_ip_address: ""
        active_node_service_tag: "XYZ765"
        passive_nodes:
            - node_service_tags: ["ABC123"]

