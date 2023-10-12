Creating node inventory
------------------------

Once the **servers are provisioned**, a list of reachable nodes can be fetched using the below command: ::

    ansible-playbook post_provision.yml


This creates a node inventory in ``/opt/omnia``.  ::

    cat /opt/omnia/node_inventory
    10.5.0.100 service_tag=XXXXXXX operating_system=RedHat
    10.5.0.101 service_tag=XXXXXXX operating_system=RedHat
    10.5.0.102 service_tag=XXXXXXX operating_system=Rocky
    10.5.0.103 service_tag=XXXXXXX operating_system=Rocky


To create an inventory when `Building Clusters <BuildingClusters/index.html>`_, use the reachable nodes' IP addresses from the above output to assign manager, compute and login groups. For more information on the inventory file used, `click here <../samplefiles.html>`_.
