IP rule assignment
===================

This playbook is used for updating IP rule of the additional configured NICs.

.. note:: ``ip_rule_assignment`` is only supported for clusters running on Ubuntu OS.

**Prerequisites**

* You must run ``server_spec_update.yml`` playbook before trying to update the IP rule.

* Ensure that all applicable properties are provided in the inventory file, as mentioned below:

        * ``nic_name``: The name of the additional nic on which user wants to configure the ip rule.
        * ``gateway``: The gateway through which the NIC is connected to the switch.
        * ``metric``: Network metric value is a value assigned to an IP route for a network interface that indicates the cost of using that route.

**Running the playbook**

    1. Change directory using the following command: ::

        cd utils/ip_rule_assignment

    2. Use the following command to execute the playbook: ::

        ansible-playbook ip_rule_assignment.yml -i inventory

**Sample inventory**

::

     all:
       hosts:
         waconode:
           nic_info:
             - { nic_name: eno20195np0, gateway: 10.10.1.254, metric: 101 }
             - { nic_name: eno20295np0, gateway: 10.10.2.254, metric: 102 }
             - { nic_name: eno20095np0, gateway: 10.10.3.254, metric: 103 }
             - { nic_name: eno19995np0, gateway: 10.10.4.254, metric: 104 }
             - { nic_name: eno19595np0, gateway: 10.10.5.254, metric: 105 }
             - { nic_name: eno19695np0, gateway: 10.10.6.254, metric: 106 }
             - { nic_name: eno19795np0, gateway: 10.10.7.254, metric: 107 }
             - { nic_name: eno19895np0, gateway: 10.10.8.254, metric: 108 }
         node02:
           nic_info:
             - { nic_name: enp129s0f0np0, gateway: 10.11.1.254, metric: 101 }
             - { nic_name: enp33s0f0np0, gateway: 10.11.2.254, metric: 102 }

* For an example inventory template, go to ``omnia/examples/ip_rule_inv_template``.