Kubernetes plugin for RoCE NIC
===============================

Install the plugin
-------------------

**Prerequisites**

    * Ensure Kubernetes is set up on the cluster with ``flannel`` as the input for the ``k8s_cni`` parameter. For The complete list of parameters, `click here <schedulerinputparams.html#id11>`_.
    * Ensure that the ``bcm_roce`` drivers are installed on the nodes.
    * Ensure that additional NICs have been configured using the ``server_spec_update.yml`` playbook. For more information on how to configure additional NICs, `click here <../InstallingProvisionTool/AdditionalNIC.html>`_.
    * Ensure that the ``{"name": "roce_plugin"}`` entry is present in the ``software_config.json`` and the same config has been used while executing the ``local_repo.yml`` playbook.
    * Ensure to update the below mentioned parameters in ``input/roce_plugin_config.yml``:

            * ``name``:  This field captures the interface name of the RoCE NIC.
            * ``range``: This field captures the IP range for the RoCE NIC.
            * ``gateway``: This field captures the gateway value to the RoCE NIC interface.

      Here is an example of the ``input/roce_plugin_config.yml``: ::

          interfaces:
            - name: eth1
              range: 192.168.1.0/24
              gateway: 192.168.1.1
            - name: eth2
              range: 192.168.2.0/24
              gateway: 192.168.2.1
            - name: eth3
              range: 192.168.3.0/24
              gateway: 192.168.3.1
            - name: eth4
              range: 192.168.4.0/24
              gateway: 192.168.4.1
            - name: eth5
              range: 192.168.5.0/24
              gateway: 192.168.5.1
            - name: eth6
              range: 192.168.6.0/24
              gateway: 192.168.6.1
            - name: eth7
              range: 192.168.7.0/24
              gateway: 192.168.7.1
            - name: eth8
              range: 192.168.8.0/24
              gateway: 192.168.8.1

**To run the playbook**

Run the playbook using the following commands: ::

    cd omnia/scheduler
    ansible-playbook deploy_roce_plugin.yml -i inventory

Where the inventory should be the same as the one used to setup Kubernetes on the cluster.

Delete the plugin
------------------

**To run the playbook**

Run the playbook using the following commands: ::

    cd omnia/scheduler
    ansible-playbook delete_roce_plugin.yml -i inventory