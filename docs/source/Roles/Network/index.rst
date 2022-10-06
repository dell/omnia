Network
=======

In your HPC cluster, connect the Mellanox InfiniBand switches using the Fat-Tree topology. In the fat-tree topology, switches in layer 1 are connected through the switches in the upper layer, i.e., layer 2. And, all the compute nodes in the cluster, such as PowerEdge servers and PowerVault storage devices, are connected to switches in layer 1. With this topology in place, we ensure that a 1x1 communication path is established between the compute nodes. For more information on the fat-tree topology, see `Designing an HPC cluster with Mellanox infiniband-solutions <https://community.mellanox.com/s/article/designing-an-hpc-cluster-with-mellanox-infiniband-solutions>`_.

.. note:: From Omnia 1.4, the Subnet Manager runs on the target Infiniband switches and not the control plane.

Omnia uses the server-based Subnet Manager (SM). SM runs in a Kubernetes namespace on the control plane. To enable the SM, Omnia configures the required parameters in the ``opensm.conf`` file. Based on the requirement, the parameters can be edited.

Some of the network features Omnia offers are:

1. Mellanox OFED

2. Infiniband switch configuration


+------------------------------+--------------------------+-----------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Name                         | Default, accepted values | Required? | Purpose                                                                                                                                                                                 |
+==============================+==========================+===========+=========================================================================================================================================================================================+
| mlnx_ofed_offline_path       |                          | FALSE     | Absolute path to local copy of .tgz file containing mlnx_ofed   package.  The package can be downloaded   from https://network.nvidia.com/products/infiniband-drivers/linux/mlnx_ofed/. |
+------------------------------+--------------------------+-----------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| mlnx_ofed_version            | 5.7-1.0.2.0              | FALSE     | Indicates the version of mlnx_ofed to be downloaded. If   ``mlnx_ofed_offline_path`` is not given, declaring this variable is   mandatory.                                              |
+------------------------------+--------------------------+-----------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| mlnx_ofed_add_kernel_support | FALSE                    | TRUE      | Indicates whether the kernel needs to be upgraded to be compatible with   mlnx_ofed.                                                                                                    |
+------------------------------+--------------------------+-----------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+




**Infiniband Switch Configuration**

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

Before running infiniband.yml, ensure that SSL Secure Cookies are disabled also HTTP and JSON Gateway need to be enabled on your switch. This can be verified by running:

``show web`` (To check if SSL Secure Cookies is disabled and HTTP is enabled)

``show json-gw`` (To check if JSON Gateway is enabled)

In case any of these services are not in the state required, run:

``no web https ssl`` secure-cookie enable (To disable SSL Secure Cookies)

``web http enable`` (To enable the HTTP gateway)

``json-gw enable`` (To enable the JSON gateway)


When connecting to a new or factory reset switch, the configuration wizard requests to execute an initial configuration:

(Recommended) If the user enters 'no', they still have to provide the admin and monitor passwords.

If the user enters 'yes', they will also be prompted to enter the hostname for the switch, DHCP details, IPv6 details, etc.

.. note::
    * When initializing a factory reset switch, the user needs to ensure DHCP is enabled and an IPv6 address is not assigned. Omnia will assign an IP address to the Infiniband switch using DHCP with all other configurations.

    * All ports intended for splitting need to be enabled before running the playbook.

**Running the playbook**

If ``enable_split_port`` is **TRUE**, run ``ansible-playbook infiniband_switch_config.yml -i inventory -e ib_username="" -e ib_password="" -e ib_admin_password="" -e ib_monitor_password=""  -e ib_default_password="" -e ib_switch_type ="xdr"``

If ``enable_split_port`` is **FALSE**, run ``ansible-playbook infiniband_switch_config.yml -i inventory -e ib_username="" -e ib_password=""  -e ib_switch_type =""``

Where ``ib_username`` is the username used to authenticate into the switch.
Where ``ib_password`` is the password used to authenticate into the switch.
Where ``ib_admin_password`` is the intended password to authenticate into the switch after ``infiniband_switch_config.yml`` has run.
Where ``ib_monitor_password`` is the mandatory password required while running the initial configuration wizard on the Inifiniband switch.
Where ``ib_default_password`` is the password used to authenticate into factory reset/fresh-install switches.
Where ``ib_switch_type`` refers to the model of the switch: HDR/EDR

.. note::

    * Passwords should contain 8-64 characters.

    * Passwords should be different than username.

    * Passwords should be different than 5 previous passwords.

    * Passwords should contain at least one of each: Lowercase, uppercase and digits.



