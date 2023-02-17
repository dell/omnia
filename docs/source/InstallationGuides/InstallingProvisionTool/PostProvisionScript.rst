After Running the Provision Tool
--------------------------------

Once the **servers are provisioned**, run the post provision script to:

* Create ``node_inventory`` in ``/opt/omnia`` listing provisioned nodes. ::

    cat /opt/omnia/node_inventory
    172.29.0.100 service_tag=XXXXXXX operating_system=RedHat
    172.29.0.101 service_tag=XXXXXXX operating_system=RedHat
    172.29.0.102 service_tag=XXXXXXX operating_system=Rocky
    172.29.0.103 service_tag=XXXXXXX operating_system=Rocky


To run the script, use the below command:::

    ansible-playbook post_provision.yml

