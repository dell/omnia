After running the provision tool
--------------------------------

Once the **servers are provisioned**, run the post provision script to:

* Create ``node_inventory`` in ``/opt/omnia`` listing provisioned nodes. ::

    cat /opt/omnia/node_inventory
    10.5.0.100 service_tag=XXXXXXX operating_system=RedHat
    10.5.0.101 service_tag=XXXXXXX operating_system=RedHat
    10.5.0.102 service_tag=XXXXXXX operating_system=Rocky
    10.5.0.103 service_tag=XXXXXXX operating_system=Rocky


To run the script, use the below command:::

    ansible-playbook post_provision.yml

