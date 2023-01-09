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

    * After running ``provision.yml``, the file ``input/provision_config.yml`` will be encrypted. To edit the file, use the command: ``ansible-vault edit provision_config.yml --vault-password-file .provision_vault_key``

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

**Using multiple versions of a given OS**

Omnia now supports deploying different versions of the same OS. With each run of ``provision.yml``, a new deployable OS image is created with a distinct type (rocky or RHEL) and version (8.0, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7) depending on the values provided in ``input/provision_config.yml``.



.. note:: for Rocky Always deploy the DVD (Full) Edition of the OS on Compute Nodes.

