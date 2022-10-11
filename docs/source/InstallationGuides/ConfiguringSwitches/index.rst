Configuring Switches
=====================

Configuring Infiniband Switches
--------------------------------

Depending on the number of ports available on your Infiniband switch, they can be classified into:
    - EDR Switches (36 ports)
    - HDR Switches (40 ports)

Input the configuration variables into the ``infiniband_edr_input.yml`` or ``infiniband_hdr_input.yml`` as appropriate:

+-------------------------+--------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Name                    | Default, Accepted values | Required? | Purpose                                                                                                                                                                |
+=========================+==========================+===========+========================================================================================================================================================================+
| enable_split_port       | false, true              | TRUE      | Indicates whether ports are to be split                                                                                                                                |
+-------------------------+--------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ib_split_ports          |                          | FALSE     | Stores the split configuration of the ports. Accepted formats are   comma-separated (EX: "1,2"), ranges (EX: "1-10"),   comma-separated ranges (EX: "1,2,3-8,9,10-12") |
+-------------------------+--------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| snmp_trap_destination   |                          | FALSE     | The IP address of the SNMP Server where the event trap will be sent. If   this variable is left blank, SNMP will be disabled.                                          |
+-------------------------+--------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| snmp_community_name     | public                   |           | The “SNMP community string” is like a user ID or password that allows   access to a router's or other device's statistics.                                             |
+-------------------------+--------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| cache_directory         |                          |           | Cache location used by OpenSM                                                                                                                                          |
+-------------------------+--------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| log_directory           |                          |           | The directory where temporary files of opensm are stored. Can be set to   the default directory or enter a directory path to store temporary files.                    |
+-------------------------+--------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ib 1/(1-xx) config      | "no shutdown"                        | Indicates the required state of ports 1-40 (depending on the value of   1/x)                                                                                           |
+-------------------------+--------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| save_changes_to_startup | false, true              |           | Indicates whether the switch configuration is to persist across reboots                                                                                                |
+-------------------------+--------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

**Before you run the playbook**

Before running infiniband.yml, ensure that SSL Secure Cookies are disabled. Also, HTTP and JSON Gateway need to be enabled on your switch. This can be verified by running:

``show web`` (To check if SSL Secure Cookies is disabled and HTTP is enabled)

``show json-gw`` (To check if JSON Gateway is enabled)

In case any of these services are not in the state required, run:

``no web https ssl secure-cookie enable`` (To disable SSL Secure Cookies)

``web http enable`` (To enable the HTTP gateway)

``json-gw enable`` (To enable the JSON gateway)


When connecting to a new or factory reset switch, the configuration wizard requests to execute an initial configuration:

(Recommended) If the user enters 'no', they still have to provide the admin and monitor passwords.

If the user enters 'yes', they will also be prompted to enter the hostname for the switch, DHCP details, IPv6 details, etc.

.. note::
    * When initializing a factory reset switch, the user needs to ensure DHCP is enabled and an IPv6 address is not assigned. Omnia will assign an IP address to the Infiniband switch using DHCP with all other configurations.

    * All ports intended for splitting need to be enabled before running the playbook.

**Running the playbook**

If ``enable_split_port`` is **TRUE**, run ``ansible-playbook infiniband_switch_config.yml -i inventory -e ib_username="" -e ib_password="" -e ib_admin_password="" -e ib_monitor_password=""  -e ib_default_password="" -e ib_switch_type =""``

If ``enable_split_port`` is **FALSE**, run ``ansible-playbook infiniband_switch_config.yml -i inventory -e ib_username="" -e ib_password=""  -e ib_switch_type =""``


* Where ``ib_username`` is the username used to authenticate into the switch.

* Where ``ib_password`` is the password used to authenticate into the switch.

* Where ``ib_admin_password`` is the intended password to authenticate into the switch after ``infiniband_switch_config.yml`` has run.

* Where ``ib_monitor_password`` is the mandatory password required while running the initial configuration wizard on the Inifiniband switch.

* Where ``ib_default_password`` is the password used to authenticate into factory reset/fresh-install switches.

* Where ``ib_switch_type`` refers to the model of the switch: HDR/EDR

.. note::

 * ``ib_admin_password`` and ``ib_monitor_password`` have the following constraints:

    * Passwords should contain 8-64 characters.

    * Passwords should be different than username.

    * Passwords should be different than 5 previous passwords.

    * Passwords should contain at least one of each: Lowercase, uppercase and digits.

 * The inventory file should be a list of IPs separated by newlines. Check out the device_ip_list.yml section in `Sample Files <https://omnia-documentation.readthedocs.io/en/latest/samplefiles.html>`_


Configuring Ethernet Switches
-----------------------------

* Edit the ``ethernet_tor_input.yml`` file for all S3* and S4* PowerSwitches such as S3048-ON, S4048T-ON, S4112F-ON, S4048-ON, S4048T-ON, S4112F-ON, S4112T-ON, and S4128F-ON.

+-------------------------+-------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Variables               | Default, choices                                                                    | Description                                                                                                                                                                                                                                                                                                                                |
+=========================+=====================================================================================+============================================================================================================================================================================================================================================================================================================================================+
| os10_config             | "interface vlan1",   "exit"                                                         | Global configurations for the switch.                                                                                                                                                                                                                                                                                                      |
+-------------------------+-------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| os10_interface          | By default: Port description is provided   and Each interface is set to "up" state. | Update the individual interfaces of the   PowerSwitch S3048-ON (ToR Switch). The interfaces are from ethernet   1/1/1 to ethernet 1/1/52. For more information about the   interfaces, see the Supported interface keys of PowerSwitch S3048-ON (ToR   Switch). Note: The playbooks will fail if any invalid configurations are   entered. |
|                         |                                                                                     |                                                                                                                                                                                                                                                                                                                                            |
+-------------------------+-------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| save_changes_to_startup | false, true                                                                         | Change it to "true" only when   you are certain that the updated configurations and commands are valid.   WARNING: When set to "true", the startup configuration file is   updated. If incorrect configurations or commands are entered, the Ethernet   switches may not operate as expected.                                              |
+-------------------------+-------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

* Edit the ``ethernet_input.yml`` file for Dell PowerSwitch S5232F-ON and all other PowerSwitches except S3* and S4* switches.

+----------------------------+-------------------------------------------------------------------------------------------------------------+-----------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Name                       | Default, accepted values                                                                                    | Required? | Purpose                                                                                                                                                                                                               |
+============================+=============================================================================================================+===========+=======================================================================================================================================================================================================================+
| os10_config                |  - "interface vlan1"                                                                                        | TRUE      | Global configurations for the   switch.                                                                                                                                                                               |
|                            |          - "exit"                                                                                           |           |                                                                                                                                                                                                                       |
+----------------------------+-------------------------------------------------------------------------------------------------------------+-----------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| breakout_value             | **10g-4x**,  25g-4x, 40g-1x, 50g-2x, 100g-1x                                                                | TRUE      | By default, all ports are   configured in the 10g-4x breakout mode in which a QSFP28 or QSFP+ port is   split into four 10G interfaces. For more information about the breakout   modes, see Configure breakout mode. |
+----------------------------+-------------------------------------------------------------------------------------------------------------+-----------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| snmp_trap_destination      |                                                                                                             | FALSE     |  The trap destination IP address is the IP   address of the SNMP Server where the trap will be sent. Ensure that the SNMP   IP is valid.                                                                              |
+----------------------------+-------------------------------------------------------------------------------------------------------------+-----------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ethernet 1/1/(1-34) config | By default:                                                                                                 | TRUE      | By default, all ports are   brought up in admin UP state                                                                                                                                                              |
|                            |      Port description is provided.                                                                          |           +-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                            |      Each interface is set to "up" state.                                                                   |           | Update   the individual interfaces of the Dell PowerSwitch S5232F-ON.                                                                                                                                                 |
|                            |      The fanout/breakout mode for 1/1/1 to 1/1/31 is as per the value set in the   breakout_value variable. |           |      The interfaces are from ethernet 1/1/1 to ethernet 1/1/34. By default, the   breakout mode is set for 1/1/1 to 1/1/31.                                                                                           |
|                            |                                                                                                             |           |      Note: The playbooks will fail if any invalid configurations are entered.                                                                                                                                         |
+----------------------------+-------------------------------------------------------------------------------------------------------------+-----------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| save_changes_to_startup    | FALSE                                                                                                       | TRUE      | Change it to "true"   only when you are certain that the updated configurations and commands are   valid.                                                                                                             |
|                            |                                                                                                             |           |      WARNING: When set to "true", the startup configuration file is   updated. If incorrect configurations or commands are entered, the Ethernet   switches may not operate as expected.                              |
+----------------------------+-------------------------------------------------------------------------------------------------------------+-----------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

* When initializing a factory reset switch, the user needs to ensure DHCP is enabled and an IPv6 address is not assigned. Omnia will assign an IP address to the switch using DHCP with all other configurations.


**Running the playbook**

*	``cd omnia/network``

*	``ansible-playbook ethernet_switch_config.yml -i inventory -e ethernet_switch_username=”” -e ethernet_switch_password=””``

* Where ``ethernet_switch_username`` is the username used to authenticate into the switch.

* The inventory file should be a list of IPs separated by newlines. Check out the device_ip_list.yml section in `Sample Files <https://omnia-documentation.readthedocs.io/en/latest/samplefiles.html>`_

* Where ``ethernet_switch_password`` is the username used to authenticate into the switch.








