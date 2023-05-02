Provisioning the cluster
--------------------------

Edit the ``input/provision_config.yml`` file to update the required variables. A list of the variables required is available by `discovery mechanism <DiscoveryMechanisms/index.html>`_.

.. note:: The first PXE device on target nodes should be the designated active NIC for PXE booting.

    .. image:: ../../images/BMC_PXE_Settings.png

Optional configurations managed by the provision tool
+++++++++++++++++++++++++++++++++++++++++++++++++++++

**Installing CUDA**

    **Using the provision tool**

        * If ``cuda_toolkit_path`` is provided  in ``input/provision_config.yml`` and NVIDIA GPUs are available on the target nodes, CUDA packages will be deployed post provisioning without user intervention.

    **Using the Accelerator playbook**

        * CUDA can also be installed using `accelerator.yml <../../Roles/Accelerator/index.html>`_ after provisioning the servers (Assuming the provision tool did not install CUDA packages).

    .. note::
        * The CUDA package can be downloaded from `here <https://developer.nvidia.com/cuda-downloads>`_
        * CUDA requires an additional reboot while being installed. While this is taken care of by Omnia, users are required to wait an additional few minutes when running the provision tool with CUDA installation for the target nodes to come up.


**Installing OFED**

    **Using the provision tool**

        * If ``mlnx_ofed_path`` is provided  in ``input/provision_config.yml`` and Mellanox NICs are available on the target nodes, OFED packages will be deployed post provisioning without user intervention.

    **Using the Network playbook**

        * OFED can also be installed using `network.yml <../../Roles/Network/index.html>`_ after provisioning the servers (Assuming the provision tool did not install OFED packages).

        .. note:: The OFED package can be downloaded from `here <https://network.nvidia.com/products/infiniband-drivers/linux/mlnx_ofed/>`_ .

**Assigning infiniband IPs**


When ``ib_nic_subnet`` is provided in ``input/provision_config.yml``, the infiniband NIC on target nodes are assigned IPv4 addresses within the subnet without user intervention. When PXE range and Infiniband subnet are provided, the infiniband NICs will be assigned IPs with the same 3rd and 4th octets as the PXE NIC.

* For example on a target node, when the PXE NIC is assigned 10.5.0.101, and the Infiniband NIC is assigned 10.10.0.101 (where ``ib_nic_subnet`` is 10.10.0.0).

.. note::  The IP is assigned to the interface **ib0** on target nodes only if the interface is present in **active** mode. If no such NIC interface is found, xCAT will list the status of the node object as failed.

**Assigning BMC IPs**

When target nodes are discovered via SNMP or mapping files (ie ``discovery_mechanism`` is set to snmp or mapping in ``input/provision_config.yml``), the ``bmc_nic_subnet`` in ``input/provision_config.yml`` can be used to assign BMC IPs to iDRAC without user intervention. When PXE range and BMC subnet are provided, the iDRAC NICs will be assigned IPs with the same 3rd and 4th octets as the PXE NIC.

* For example on a target node, when the PXE NIC is assigned 10.5.0.101, and the iDRAC NIC is assigned 10.3.0.101 (where ``bmc_nic_subnet`` is 10.3.0.0).

**Using multiple versions of a given OS**

Omnia now supports deploying different versions of the same OS. With each run of ``provision.yml``, a new deployable OS image is created with a distinct type (rocky or RHEL) and version (8.0, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7) depending on the values provided in ``input/provision_config.yml``.

.. note::
    * While Omnia deploys the minimal version of the OS, the multiple version feature requires that the Rocky full (DVD) version of the OS be provided.
    * The multiple OS feature is only available with Rocky 8.7 when xCAT 2.16.5 is in use. [Currently, Omnia uses 2.16.4]


**DHCP routing for internet access**

Omnia now supports DHCP routing via the control plane. To enable routing, update the ``primary_dns`` and ``secondary_dns`` in ``input/provision_config.yml`` with the appropriate IPs (hostnames are currently not supported). For compute nodes that are not directly connected to the internet (ie only PXE network is configured), this configuration allows for internet connectivity.

**Disk partitioning**

Omnia now allows for customization of disk partitions applied to remote servers. The disk partition ``desired_capacity`` has to be provided in MB. Valid ``mount_point`` values accepted for disk partition are ``/home``, ``/var``, ``/tmp``, ``/usr``, ``swap``. Default partition size provided for ``/boot`` is 1024MB, ``/boot/efi`` is 256MB and the remaining space to ``/`` partition.  Values are accepted in the form of JSON list such as:

::

    disk_partition:
        - { mount_point: "/home", desired_capacity: "102400" }
        - { mount_point: "swap", desired_capacity: "10240" }



Running the provision tool
++++++++++++++++++++++++++++

To deploy the Omnia provision tool, run the following command ::

    cd provision
    ansible-playbook provision.yml


``provision.yml`` runs in three stages that can be called individually:

**Preparing the control plane**

a. Verifies pre-requisites such as SELinux and xCAT services status.
b. Installs required tool packages.
c. Verifies and updates firewall settings.
d. Installs xCAT.
e. Configures xCAT databases basis ``input/provision_config.yml``.

To call this playbook individually, ensure that ``input/provision_config.yml`` is updated and then run::

    ansible-playbook prepare_cp.yml

**Creating/updating the repositories**

* Creates and updates all repositories required locally.

* This playbook also calls the ``airgap.yml`` script for RHEL repository requirements. For more information on this, `click here <../../Roles/Airgap/index.html>`_.

* To call this playbook individually, ensure that ``prepare_cp.yml`` has run at least once and then run::

    ansible-playbook repo_manipulate.yml


**Discovering/provisioning the nodes**

a. Discovers all target servers based on specifications in ``input/provision_config.yml``.

b. Provisions all discovered servers.

c. PostgreSQL database is set up with all relevant cluster information such as MAC IDs, hostname, admin IP, infiniband IPs, BMC IPs etc.

    To access the DB, run: ::

            psql -U postgres

            \c omniadb


    To view the schema being used in the cluster: ``\dn``

    To view the tables in the database: ``\dt``

    To view the contents of the ``nodeinfo`` table: ``select * from cluster.nodeinfo;`` ::


                    id  | serial  |        node        |            hostname            |     admin_mac     |   admin_ip   |    bmc_ip    |    ib_ip     |   status   | bmc_mode |   switch_ip    | switch_name | switch_port
                    ----+---------+--------------------+--------------------------------+-------------------+--------------+--------------+--------------+------------+----------+---------------+-------------+-------------
                      1 | XXXXXXX | omnia-node00001    | omnia-node00001.omnia.test     | ec:2a:72:34:f7:26 |  10.5.0.101  | 10.19.0.101   | 10.10.0.101  | booted     |          | 10.96.28.132   | switch1     | 2
                      2 | XXXXXXX | omnia-node00002    | omnia-node00002.omnia.test     |                   |  10.5.0.102  | 10.19.0.102   | 10.10.0.102  |            |          | 10.96.28.132   | switch1     | 3
                      3 | XXXXXXX | omnia-node00003    | omnia-node00003.omnia.test     |                   |  10.5.0.103  | 10.19.0.103   | 10.10.0.103  |            |          | 10.96.28.132   | switch1     | 4
                      4 | XXXXXXX | omnia-node00004    | omnia-node00004.omnia.test     | 2c:ea:7f:3d:6b:98 |  10.5.0.104  | 10.19.0.104   | 10.10.0.104  | installing |          | 10.96.28.132   | switch1     | 5
                      5 | XXXXXXX | omnia-node00005    | omnia-node00005.omnia.test     |                   |  10.5.0.105  | 10.19.0.105   | 10.10.0.105  |            |          | 10.96.28.132   | switch1     | 6
                      6 | XXXXXXX | omnia-node00006    | omnia-node00006.omnia.test     |                   |  10.5.0.106  | 10.19.0.106   | 10.10.0.106  |            |          | 10.96.28.132   | switch1     | 7
                      7 | XXXXXXX | omnia-node00007    | omnia-node00007.omnia.test     | 4c:d9:8f:76:48:2e |  10.5.0.107  | 10.19.0.107   | 10.10.0.107  | booted     |          | 10.96.28.132   | switch1     | 8
                      8 | XXXXXXX | omnia-node00008    | omnia-node00008.omnia.test     |                   |  10.5.0.108  | 10.19.0.108   | 10.10.0.108  |            |          | 10.96.28.132   | switch1     | 1
                      9 | XXXXXXX | omnia-node00009    | omnia-node00009.omnia.test     |                   |  10.5.0.109  | 10.19.0.109   | 10.10.0.109  | failed     |          | 10.96.28.132   | switch1     | 10
                    10  | XXXXXXX | omnia-node00010    | omnia-node00010.omnia.test     |                   |  10.5.0.110  | 10.19.0.110   | 10.10.0.110  |            |          | 10.96.28.132   | switch1     | 12
                    11  | XXXXXXX | omnia-node00011    | omnia-node00011.omnia.test     |                   |  10.5.0.111  | 10.19.0.111   | 10.10.0.111  | failed     |          | 10.96.28.132   | switch1     | 13
                    12  | XXXXXXX | omnia-node00012    | omnia-node00012.omnia.test     |                   |  10.5.0.112  | 10.19.0.112   | 10.10.0.112  |            |          | 10.96.28.132   | switch1     | 14


Possible values of status are static, powering-on, installing, bmcready, booting, post-booting, booted, failed. The status will be updated every 3 minutes.

.. note:: For nodes listing status as 'failed', provisioning logs can be viewed in ``/var/log/xcat/xcat.log`` on the target nodes.


To call this playbook individually, ensure that ``repo_manipulate.yml`` has run at least once and then run::

    ansible-playbook discovery_provision.yml



.. note::

    * If the cluster does not have access to the internet, AppStream will not function.  To provide internet access through the control plane (via the PXE network NIC), update ``primary_dns`` and ``secondary_dns`` in ``provision_config.yml`` and run ``provision.yml``

    * All ports required for xCAT to run will be opened (For a complete list, check out the `Security Configuration Document <../../SecurityConfigGuide/ProductSubsystemSecurity.html#firewall-settings>`_).

    * After running ``provision.yml``, the file ``input/provision_config.yml`` will be encrypted. To edit the file, use the command: ``ansible-vault edit provision_config.yml --vault-password-file .provision_vault_key``

    * To re-provision target servers ``provision.yml`` can be re-run with a new inventory file that contains a list of admin (PXE) IPs. For more information, `click here <../reprovisioningthecluster.rst>`_

    * Post execution of ``provision.yml``, IPs/hostnames cannot be re-assigned by changing the mapping file. However, the addition of new nodes is supported as explained below.


.. warning::

    * Once xCAT is installed, restart your SSH session to the control plane to ensure that the newly set up environment variables come into effect.
    * To avoid breaking the passwordless SSH channel on the control plane, do not run ``ssh-keygen`` commands post execution of ``provision.yml``.


