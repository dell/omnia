Provision
==========

Before You Run The Provision Tool
---------------------------------

* (Recommended) Run ``prereq.sh`` to get the system ready to deploy Omnia. Alternatively, ensure that `Ansible 2.12.9 <https://docs.ansible.com/ansible/latest/reference_appendices/release_and_maintenance.html>`_ and `Python 3.8 <https://www.python.org/downloads/release/python-380/>`_ are installed on the system. SELinux should also be disabled.
* To provision the bare metal servers, download one of the following ISOs for deployment:

    1. `Rocky 8 <https://rockylinux.org/>`_

    2. `RHEL 8.x <https://www.redhat.com/en/enterprise-linux-8>`_

* To dictate IP address/MAC mapping, a host mapping file can be provided. If the mapping file is not provided and the variable is left blank, a default mapping file will be created by querying the switch. Use the `pxe_mapping_file.csv <../../Samplefiles.html>`_ to create your own mapping file.

* Ensure that all connection names under the network manager match their corresponding device names. ::

    nmcli connection

In the event of a mismatch, edit the file  ``/etc/sysconfig/network-scripts/ifcfg-<nic name>`` using vi editor.

* All target hosts should be set up in PXE mode before running the playbook.

* If RHEL is in use on the control plane, enable RedHat subscription. Not only does Omnia not enable RedHat subscription on the control plane, package installation may fail if RedHat subscription is disabled.

* Users should also ensure that all repos are available on the RHEL control plane.

* Ensure that the ``pxe_nic`` and ``public_nic`` are in the firewalld zone: public.

 .. Note::

    * After configuration and installation of the cluster, changing the control plane is not supported. If you need to change the control plane, you must redeploy the entire cluster.

    * If there are errors while executing any of the Ansible playbook commands, then re-run the playbook.

Input Parameters for Provision Tool
------------------------------------

Fill in all provision-specific parameters in ``input/provision_config.yml``

+----------------------------------+------------------------------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Name                             | Default, Accepted Values                       | Required? | Additional Information                                                                                                                                                                                                                                                                                                                                                                                                                                     |
+==================================+================================================+===========+============================================================================================================================================================================================================================================================================================================================================================================================================================================================+
| public_nic                       | eno2                                           | required  | The NIC/ethernet card that is connected to the public internet.                                                                                                                                                                                                                                                                                                                                                                                            |
+----------------------------------+------------------------------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| admin_nic                        | eno1                                           | required  | The NIC/ethernet card that is used for shared LAN over Management (LOM)   capability.                                                                                                                                                                                                                                                                                                                                                                      |
+----------------------------------+------------------------------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| admin_nic_subnet                 | 172.29.0.0                                     | required  | The intended subnet for shared LOM capability. Note that since   the last 16 bits/2 octets of IPv4 are dynamic, please ensure that the   parameter value is set to x.x.0.0.                                                                                                                                                                                                                                                                                |
+----------------------------------+------------------------------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| pxe_nic                          | eno1                                           | required  | This NIC used to obtain routing information.                                                                                                                                                                                                                                                                                                                                                                                                               |
+----------------------------------+------------------------------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| pxe_nic_start_range              | 172.29.0.100                                   | required  | The start of the DHCP    range used to assign IPv4 addresses. When the PXE range and BMC subnet   are provided, corresponding NICs will be assigned IPs with the same 3rd and   4th octets. Ensure that these ranges contain enough IPs to be double the   number of iDRACs present in the cluster.                                                                                                                                                        |
+----------------------------------+------------------------------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| pxe_nic_end_range                | 172.29.0.200                                   | required  | The end of the DHCP    range used to assign IPv4 addresses. When the PXE range and BMC subnet   are provided, corresponding NICs will be assigned IPs with the same 3rd and   4th octets.   Ensure that these ranges   contain enough IPs to be double the number of iDRACs present in the cluster.                                                                                                                                                        |
+----------------------------------+------------------------------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ib_nic_subnet                    |                                                | optional  | If provided, Omnia will assign static IPs to IB NICs on the compute nodes   within the provided subnet. Note that since the last 16 bits/2 octets of IPv4   are dynamic, please ensure that the parameter value is set to x.x.0.0.  When the PXE range and BMC subnet are   provided, corresponding NICs will be assigned IPs with the same 3rd and 4th   octets.  IB nics should be prefixed ib.                                                          |
+----------------------------------+------------------------------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| bmc_nic_subnet                   |                                                | optional  | If provided, Omnia will assign static IPs to IB NICs on the compute nodes   within the provided subnet. Note that since the last 16 bits/2 octets of IPv4   are dynamic, please ensure that the parameter value is set to x.x.0.0. When   the PXE range and BMC subnet are provided, corresponding NICs will be   assigned IPs with the same 3rd and 4th octets.                                                                                           |
+----------------------------------+------------------------------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| pxe_mapping_file_path            |                                                | optional  | The mapping file consists of the MAC address and its respective IP   address and hostname. If static IPs are required, create a csv file in the   format MAC,Hostname,IP. A sample file is provided here:   examples/pxe_mapping_file.csv. If not provided, ensure that ``pxe_switch_ip``   is provided.                                                                                                                                                   |
+----------------------------------+------------------------------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| pxe_switch_ip                    |                                                | optional  | PXE switch that will be connected to all iDRACs for provisioning. This   switch needs to be SNMP-enabled.                                                                                                                                                                                                                                                                                                                                                  |
+----------------------------------+------------------------------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| pxe_switch_snmp_community_string | public                                         | optional  | The SNMP community string used to access statistics, MAC addresses and   IPs stored within a router or other device.                                                                                                                                                                                                                                                                                                                                       |
+----------------------------------+------------------------------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| node_name                        | node                                           | required  | The intended node name for nodes in the cluster.                                                                                                                                                                                                                                                                                                                                                                                                           |
+----------------------------------+------------------------------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| domain_name                      |                                                | required  | DNS domain name to be set for iDRAC.                                                                                                                                                                                                                                                                                                                                                                                                                       |
+----------------------------------+------------------------------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| provision_os                     | rocky, **rhel**                                | required  | The operating system image that will be used for provisioning compute   nodes in the cluster.                                                                                                                                                                                                                                                                                                                                                              |
+----------------------------------+------------------------------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| iso_file_path                    | /home/RHEL-8.4.0-20210503.1-x86_64-dvd1.iso    | required  | The path where the user places the ISO image that needs to be provisioned   in target nodes.                                                                                                                                                                                                                                                                                                                                                               |
+----------------------------------+------------------------------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| timezone                         | GMT                                            | required  | The timezone that will be set during provisioning of OS. Available   timezones are provided in provision/roles/xcat/files/timezone.txt.                                                                                                                                                                                                                                                                                                                    |
+----------------------------------+------------------------------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| language                         | en-US                                          | required  | The language that will be set during provisioning of the OS                                                                                                                                                                                                                                                                                                                                                                                                |
+----------------------------------+------------------------------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| default_lease_time               | 86400                                          | required  | Default lease time in seconds that will be used by DHCP.                                                                                                                                                                                                                                                                                                                                                                                                   |
+----------------------------------+------------------------------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| provision_password               |                                                | required  | Password used while deploying OS on bare metal servers. The Length of the   password should be at least 8 characters. The password must not contain -,\,   ',".                                                                                                                                                                                                                                                                                            |
+----------------------------------+------------------------------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| postgresdb_password              |                                                | required  | Password used to authenticate into the PostGresDB used by xCAT. Only   alphanumeric characters (no special characters) are accepted.                                                                                                                                                                                                                                                                                                                       |
+----------------------------------+------------------------------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| primary_dns                      |                                                | optional  | The primary DNS host IP queried to provide Internet access to Compute   Node (through DHCP routing)                                                                                                                                                                                                                                                                                                                                                        |
+----------------------------------+------------------------------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| secondary_dns                    |                                                | optional  | The secondary DNS host IP queried to provide Internet access to Compute   Node (through DHCP routing)                                                                                                                                                                                                                                                                                                                                                      |
+----------------------------------+------------------------------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| disk_partition                   |  - { mount_point: "",   desired_capacity: "" } | optional  | User defined disk partition applied to remote servers. The disk partition   desired_capacity has to be provided in MB. Valid mount_point values accepted   for disk partition are /home, /var, /tmp, /usr, swap. Default partition size   provided for /boot is 1024MB, /boot/efi is 256MB and the remaining space to /   partition.  Values are accepted in the   form of JSON list such as: , - { mount_point: "/home",   desired_capacity: "102400" },  |
+----------------------------------+------------------------------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

Running The Provision Tool
--------------------------

1. Edit the ``input/provision_config.yml`` file to update the required variables.

.. warning:: The IP address *192.168.25.x* is used for PowerVault Storage communications. Therefore, do not use this IP address for other configurations.

2. To deploy the Omnia provision tool, run the following command ::

    cd provision
    ansible-playbook provision.yml

3. By running ``provision.yml``, the following configurations take place:

    i. All compute nodes in cluster will be enabled for PXE boot with osimage mentioned in ``provision_config.yml``.

    ii. A PostgreSQL database is set up with all relevant cluster information such as MAC IDs, hostname, admin IP, infiniband IPs, BMC IPs etc.

            To access the DB, run: ::

                        psql -U postgres

                        \c omniadb


            To view the schema being used in the cluster: ``\dn``

            To view the tables in the database: ``\dt``

            To view the contents of the ``nodeinfo`` table: ``select * from cluster.nodeinfo`` ::

                    id | servicetag |     admin_mac     |         hostname         |   admin_ip   | bmc_ip | ib_ip

                    ----+------------+-------------------+--------------------------+--------------+--------+-------


                    1 |            | 00:c0:ff:43:f9:44 | node00001.winter.cluster | 172.29.1.253 |        |
                    2 |            | 70:b5:e8:d1:84:22 | node00002.winter.cluster | 172.29.1.254 |        |
                    3 |            | b8:ca:3a:71:25:5c | node00003.winter.cluster | 172.29.1.255 |        |
                    4 |            | 8c:47:be:c7:6f:c1 | node00004.winter.cluster | 172.29.2.0   |        |
                    5 |            | 8c:47:be:c7:6f:c2 | node00005.winter.cluster | 172.29.2.1   |        |
                    6 |            | b0:26:28:5b:80:18 | node00006.winter.cluster | 172.29.2.2   |        |
                    7 |            | b0:7b:25:de:71:de | node00007.winter.cluster | 172.29.2.3   |        |
                    8 |            | b0:7b:25:ee:32:fc | node00008.winter.cluster | 172.29.2.4   |        |
                    9 |            | d0:8e:79:ba:6a:58 | node00009.winter.cluster | 172.29.2.5   |        |
                    10|            | d0:8e:79:ba:6a:5e | node00010.winter.cluster | 172.29.2.6   |        |

   iii. Offline repositories will be created based on the OS being deployed across the cluster.

Once the playbook execution is complete, ensure that PXE boot and RAID configurations are set up on remote nodes. Users are then expected to reboot target servers to provision the OS.

.. note::

    * If the cluster does not have access to the internet, AppStream will not function.  To provide internet access through the control plane (via the PXE network NIC), update ``primary_dns`` and ``secondary_dns`` in ``provision_config.yml`` and run ``provision.yml``

    * All ports required for xCAT to run will be opened (For a complete list, check out the `Security Configuration Document <../../SecurityConfigGuide/PortsUsed/xCAT.html>`_).

    * After running ``provision.yml``, the file ``input/provision_config.yml`` will be encrypted. To edit file, use the command: ``ansible-vault edit provision_config.yml --vault-password-file .provision_vault_key``

    * To re-provision target servers ``provision.yml`` can be re-run. Alternatively, use the following steps:

         * Use ``lsdef -t osimage | grep install-compute`` to get a list of all valid OS profiles.

         * Use ``nodeset all osimage=<selected OS image from previous command>`` to provision the OS on the target server.

         * PXE boot the target server to bring up the OS.

.. warning:: Once xCAT is installed, restart your SSH session to the control plane to ensure that the newly set up environment variables come into effect.

**Adding a new node**

A new node can be added using one of two ways:

1. Using a mapping file:

    * Update the existing mapping file by appending the new entry (without the disrupting the older entries) or provide a new mapping file by pointing ``pxe_mapping_file_path`` in ``provision_config.yml`` to the new location.

    * Run ``provision.yml``.

2. Using the switch IP:

    * Run ``provision.yml`` once the switch has discovered the potential new node.


After Running the Provision Tool
--------------------------------

Once the **servers are provisioned**, run the post provision script to:

* Configure iDRAC IP or BMC IP if ``bmc_nic_subnet`` is provided in ``input/provision_config.yml``.

* Configure Infiniband static IPs on remote nodes if ``ib_nic_subnet`` is provided in ``input/provision_config.yml``.

* Set hostname for the remote nodes.

* Invoke ``network.yml`` and ``accelerator.yml`` to install OFED, CUDA toolkit and ROCm drivers.

* Create ``node_inventory`` in ``/opt/omnia`` listing provisioned nodes. ::

    cat /opt/omnia/node_inventory
    172.29.0.100 service_tag=XXXXXXX operating_system=RedHat
    172.29.0.101 service_tag=XXXXXXX operating_system=RedHat
    172.29.0.102 service_tag=XXXXXXX operating_system=Rocky
    172.29.0.103 service_tag=XXXXXXX operating_system=Rocky


.. note:: Before post provision script, verify redhat subscription is enabled using the ``rhsm_subscription.yml`` playbook in utils only if OFED or GPU accelerators are to be installed.

To run the script, use the below command:::

    ansible-playbook post_provision.yml


