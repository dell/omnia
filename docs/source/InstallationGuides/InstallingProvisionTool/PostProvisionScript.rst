After Running the Provision Tool
=================================

Once the servers are provisioned, run the post provision script to:

* Configure iDRAC IP or BMC IP if ``bmc_nic_subnet`` is provided in ``input/provision_config.yml``.

* Configure Infiniband static IPs on remote nodes if ``ib_nic_subnet`` is provided in ``input/provision_config.yml``.

* Set hostname for the remote nodes.

* Invoke ``network.yml`` and ``accelerator.yml`` to install OFED, CUDA toolkit and ROCm drivers.

* Create ``node_inventory`` in ``/opt/omnia`` listing provisioned nodes. ::

    cat /opt/omnia/node_inventory
    172.17.0.100 service_tag=XXXXXXX operating_system=RedHat
    172.17.0.101 service_tag=XXXXXXX operating_system=RedHat
    172.17.0.102 service_tag=XXXXXXX operating_system=Rocky
    172.17.0.103 service_tag=XXXXXXX operating_system=Rocky


.. note:: Before post provision script, verify redhat subscription is enabled using the ``rhsm_subscription.yml`` playbook in utils only if OFED or GPU accelerators are to be installed.

To run the script, use the below command:::

    ansible-playbook post_provision.yml


