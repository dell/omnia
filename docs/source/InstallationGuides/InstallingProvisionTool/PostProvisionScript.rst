After Running the Provision Tool
=================================

Once the servers are provisioned, run the post provision script to:

* Configure iDRAC IP or BMC IP based on ``bmc_nic_subnet`` in ``omnia/input/provision_config.yml``.

* Configure Infiniband IP on remote nodes based on ``ib_nic_subnet`` in ``omnia/input/provision_config.yml``.

* Set hostname for the remote nodes.

* Invoke ``network.yml`` and ``accelerator.yml`` to install OFED, CUDA toolkit and ROCm drivers.

* If ``ib_nic_subnet`` is provided in the ``input/provision_config.yml`` file, Infiniband NICs will be assigned static IPs.

.. note::  The prefix for IB IP is 16 by default and supports 65,534 hosts.

* Create ``node_inventory`` in /opt/omnia listing provisioned nodes. ::

    cat /opt/omnia/node_inventory
    172.17.0.100 service_tag=XXXXXXX operating_system=RedHat
    172.17.0.101 service_tag=XXXXXXX operating_system=RedHat
    172.17.0.102 service_tag=XXXXXXX operating_system=Rocky
    172.17.0.103 service_tag=XXXXXXX operating_system=Rocky

To run the script, use the below command: ::

    ansible-playbook post_provision.yml


