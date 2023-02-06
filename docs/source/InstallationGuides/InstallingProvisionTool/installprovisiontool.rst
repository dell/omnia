Running The Provision Tool
--------------------------

1. Edit the ``input/provision_config.yml`` file to update the required variables.

.. warning:: The IP address *192.168.25.x* is used for PowerVault Storage communications. Therefore, do not use this IP address for other configurations.

2. To deploy the Omnia provision tool, run the following command ::

    cd provision
    ansible-playbook provision.yml

3. By running ``provision.yml``, the following configurations take place:

a. All compute nodes in cluster will be enabled for PXE boot with osimage mentioned in ``provision_config.yml``.

b. A PostgreSQL database is set up with all relevant cluster information such as MAC IDs, hostname, admin IP, infiniband IPs, BMC IPs etc.

    To access the DB, run: ::

            psql -U postgres

            \c omniadb


    To view the schema being used in the cluster: ``\dn``

    To view the tables in the database: ``\dt``

    To view the contents of the ``nodeinfo`` table: ``select * from cluster.nodeinfo;`` ::


                    id | serial  |   node    |       hostname        | admin_mac |  admin_ip   |   bmc_ip    | ib_ip | status | bmc_mode
                    ----+---------+-----------+-----------------------+-----------+-------------+-------------+-------+--------+----------
                      1 | 4FC45X2 | node00001 | node00001.spring.test |           | 172.17.0.25 | 172.29.0.25 | 172.35.0.25 |        | static
                      2 | FBB65X2 | node00002 | node00002.spring.test |           | 172.17.0.35 | 172.29.0.35 | 172.35.0.35 |        | static



c. Offline repositories will be created based on the OS being deployed across the cluster.

d. The xCAT post bootscript is configured to assign the hostname (with domain name) on the provisioned servers.

e. If ``mlnx_ofed_path`` is provided, OFED packages will be deployed post provisioning without user intervention. Alternatively, OFED can be installed using `network.yml <../../Roles/Network/index.html>`_.

f. If ``cuda_toolkit_path`` is provided, CUDA packages will be deployed post provisioning without user intervention. Alternatively, CUDA can be installed using `accelerator.yml <../../Roles/Accelerator/index.html>`_.

g. If ``bmc_nic_subnet`` is provided, and the ``discovery_mechanism`` is set to ``snmp`` or ``mapping``, the BMC IP address will be assigned post provisioning without user intervention.
	
Once the playbook execution is complete, ensure that PXE boot and RAID configurations are set up on remote nodes. Users are then expected to reboot target servers to provision the OS.

.. note::

    * If the cluster does not have access to the internet, AppStream will not function.  To provide internet access through the control plane (via the PXE network NIC), update ``primary_dns`` and ``secondary_dns`` in ``provision_config.yml`` and run ``provision.yml``

    * All ports required for xCAT to run will be opened (For a complete list, check out the `Security Configuration Document <../../SecurityConfigGuide/ProductSubsystemSecurity.html#firewall-settings>`_).

    * After running ``provision.yml``, the file ``input/provision_config.yml`` will be encrypted. To edit the file, use the command: ``ansible-vault edit provision_config.yml --vault-password-file .provision_vault_key``

    * To re-provision target servers ``provision.yml`` can be re-run. Alternatively, use the following steps (as an example, we will be re-provisioning rhels8.6.0-x86_64-install-compute):

         * Use ``lsdef -t osimage | grep install-compute`` to get a list of all valid OS profiles.

         * Use ``nodeset all osimage=rhels8.6.0-x86_64-install-compute`` to provision the OS on the target server.

         * PXE boot the target server to bring up the OS.

    * Post execution of ``provision.yml``, IPs/hostnames cannot be re-assigned by changing the mapping file. However, the addition of new nodes is supported as explained below.

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



.. note:: While Omnia deploys the minimal version of the OS, the multiple version feature requires that the Rocky full (DVD) version of the OS be provided.

