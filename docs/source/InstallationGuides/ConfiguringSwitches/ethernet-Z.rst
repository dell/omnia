Configuring ethernet switches (Z series)
-----------------------------------------


* Edit the ``network/ethernet_zseries_input.yml`` file for all Z series PowerSwitches such as Z9332F-ON, Z9262-ON and Z9264F-ON. The default configuration is written for Z9264F-ON.

+------------------------------+-------------------------------------------------------------------------------------------------------------+-----------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Name                         | Default, accepted values                                                                                    | Required? | Purpose                                                                                                                                                                                                             |
+==============================+=============================================================================================================+===========+=====================================================================================================================================================================================================================+
| os10_config                  |  - "interface   vlan1"                                                                                      | required  | Global configurations for the switch.                                                                                                                                                                               |
|                              |  - "exit"                                                                                                   |           |                                                                                                                                                                                                                     |
+------------------------------+-------------------------------------------------------------------------------------------------------------+-----------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| breakout_value               | **10g-4x**,  25g-4x, 40g-1x, 100g-1x                                                                        | required  | By default, all ports are configured in the 10g-4x breakout mode in which   a QSFP28 or QSFP+ port is split into four 10G interfaces. For more   information about the breakout modes, see Configure breakout mode. |
+------------------------------+-------------------------------------------------------------------------------------------------------------+-----------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| snmp_trap_destination        |                                                                                                             | optional  |  The trap destination IP address is   the IP address of the SNMP Server where the trap will be sent. Ensure that   the SNMP IP is valid.                                                                            |
+------------------------------+-------------------------------------------------------------------------------------------------------------+-----------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| snmp_community_string        | public                                                                                                      | optional  |  An SNMP community string is a   means of accessing statistics stored within a router or other device.                                                                                                              |
+------------------------------+-------------------------------------------------------------------------------------------------------------+-----------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ethernet 1/1/(1-63)   config | By default:                                                                                                 | required  | By default, all ports are brought up in admin UP state                                                                                                                                                              |
|                              |      Port description is provided.                                                                          |           +---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                              |      Each interface is set to "up" state.                                                                   |           | Update the individual interfaces of the   Dell PowerSwitch S5232F-ON.                                                                                                                                               |
|                              |      The fanout/breakout mode for 1/1/1 to 1/1/61 is as per the value set in the   breakout_value variable. |           |      The interfaces are from ethernet 1/1/1 to ethernet 1/1/63. By default, the   breakout mode is set for 1/1/1 to 1/1/63.                                                                                         |
|                              |                                                                                                             |           |      Note: The playbooks will fail if any invalid configurations are entered.                                                                                                                                       |
+------------------------------+-------------------------------------------------------------------------------------------------------------+-----------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| save_changes_to_startup      | false                                                                                                       | required  | Change it to "true" only when you are certain that the updated   configurations and commands are valid.                                                                                                             |
|                              |                                                                                                             |           |      WARNING: When set to "true", the startup configuration file is   updated. If incorrect configurations or commands are entered, the Ethernet   switches may not operate as expected.                            |
+------------------------------+-------------------------------------------------------------------------------------------------------------+-----------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

* When initializing a factory reset switch, the user needs to ensure DHCP is enabled and an IPv6 address is not assigned.

* The 65th port on a Z series switch cannot be split.

    * Only odd ports support breakouts on Z9264F-ON. For more information, `click here <https://www.dell.com/support/kbdoc/en-in/000195212/powerscale-dell-z9264-switches-only-allow-breakout-cables-in-odd-port-numbers?lang=en#>`_.

.. note:: The ``breakout_value`` of a port can only be changed after un-splitting the port.

**Running the playbook**::

    cd network

    ansible-playbook ethernet_switch_config.yml -i inventory -e ethernet_switch_username=”” -e ethernet_switch_password=””

* Where ``ethernet_switch_username`` is the username used to authenticate into the switch.

* The inventory file should be a list of IPs separated by newlines. Check out the switch_inventory section in `Sample Files <https://omnia-documentation.readthedocs.io/en/latest/samplefiles.html>`_

* Where ``ethernet_switch_password`` is the password used to authenticate into the switch.



