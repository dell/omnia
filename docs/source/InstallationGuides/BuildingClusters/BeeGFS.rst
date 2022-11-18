BeeGFS Bolt On
--------------

BeeGFS is a hardware-independent POSIX parallel file system (a.k.a. Software-defined Parallel Storage) developed with a strong focus on performance and designed for ease of use, simple installation, and management.

.. image:: ../../images/BeeGFS_Structure.jpg


**Pre Requisites before installing BeeGFS client**

* If the user intends to use BeeGFS, ensure that a BeeGFS cluster has been set up with beegfs-mgmtd, beegfs-meta, beegfs-storage services running.

  Ensure that the following ports are open for TCP and UDP connectivity:

        +------+-----------------------------------+
        | Port | Service                           |
        +======+===================================+
        | 8008 | Management service (beegfs-mgmtd) |
        +------+-----------------------------------+
        | 8003 | Storage service (beegfs-storage)  |
        +------+-----------------------------------+
        | 8004 | Client service (beegfs-client)    |
        +------+-----------------------------------+
        | 8005 | Metadata service (beegfs-meta)    |
        +------+-----------------------------------+
        | 8006 | Helper service (beegfs-helperd)   |
        +------+-----------------------------------+



To open the ports required, use the following steps:

    1. ``firewall-cmd --permanent --zone=public --add-port=<port number>/tcp``

    2. ``firewall-cmd --permanent --zone=public --add-port=<port number>/udp``

    3. ``firewall-cmd --reload``

    4. ``systemctl status firewalld``



* Ensure that the nodes in the inventory have been assigned **only** these roles: manager and compute.

 .. note::

    * If the BeeGFS server (MGMTD, Meta, or storage) is running BeeGFS version 7.3.1 or higher, the security feature on the server should be disabled. Change the value of ``connDisableAuthentication`` to ``true`` in /etc/beegfs/beegfs-mgmtd.conf, /etc/beegfs/beegfs-meta.conf and /etc/beegfs/beegfs-storage.conf. Restart the services to complete the task: ::

        systemctl restart beegfs-mgmtd
        systemctl restart beegfs-meta
        systemctl restart beegfs-storage
        systemctl status beegfs-mgmtd
        systemctl status beegfs-meta
        systemctl status beegfs-storage


.. note:: BeeGFS with OFED capability is only supported on RHEL 8.3 and above due to limitations on BeeGFS. When setting up your cluster with RDMA support, check the BeeGFS documentation to provide appropriate values in ``input/storage_config.yml``.

* If the cluster runs Rocky, ensure that versions running are compatible:

+-----------------------------------------+----------------+
| Rocky OS version                        | BeeGFS version |
+=========================================+================+
| Rocky Linux 8.4: no OFED, OFED 5.3, 5.4 | 7.3.2          |
+-----------------------------------------+----------------+
| Rocky Linux 8.5: no OFED, OFED 5.5      | 7.3.2          |
+-----------------------------------------+----------------+
| Rocky Linux 8.6: no OFED, OFED 5.6      | 7.3.2          |
+-----------------------------------------+----------------+
| Rocky Linux 8.4: no OFED, OFED 5.3, 5.4 | 7.3.1          |
+-----------------------------------------+----------------+
| Rocky Linux 8.5: no OFED, OFED 5.5      | 7.3.1          |
+-----------------------------------------+----------------+
| Rocky Linux 8.6: no OFED, OFED 5.6      | 7.3.1          |
+-----------------------------------------+----------------+
| Rocky Linux 8.4: no OFED, OFED 5.3, 5.4 | 7.3.0          |
+-----------------------------------------+----------------+
| Rocky Linux 8.5: no OFED, OFED 5.5      | 7.3.0          |
+-----------------------------------------+----------------+
| Rocky Linux 8.4: no OFED, OFED 5.3, 5.4 | 7.2.8          |
+-----------------------------------------+----------------+
| Rocky Linux 8.5: no OFED, OFED 5.5      | 7.2.8          |
+-----------------------------------------+----------------+
| Rocky Linux 8.6: no OFED, OFED 5.6      | 7.2.8          |
+-----------------------------------------+----------------+
| Rocky Linux 8.4: no OFED, OFED 5.3, 5.4 | 7.2.7          |
+-----------------------------------------+----------------+
| Rocky Linux 8.5: no OFED, OFED 5.5      | 7.2.7          |
+-----------------------------------------+----------------+
| Rocky Linux 8.6: no OFED, OFED 5.6      | 7.2.7          |
+-----------------------------------------+----------------+
| Rocky Linux 8.5: no OFED, OFED 5.5      | 7.2.6          |
+-----------------------------------------+----------------+
| Rocky Linux 8.6: no OFED, OFED 5.6      | 7.2.6          |
+-----------------------------------------+----------------+
| Rocky Linux 8.4: no OFED, OFED 5.3, 5.4 | 7.2.5          |
+-----------------------------------------+----------------+
| Rocky Linux 8.4: no OFED, OFED 5.3, 5.4 | 7.2.4          |
+-----------------------------------------+----------------+

**Installing the BeeGFS client via Omnia**

After the required parameters are filled in ``input/storage_config.yml``, Omnia installs BeeGFS on manager and compute nodes while executing the ``omnia.yml`` playbook. ::

.. note::
    * BeeGFS client-server communication can take place through TCP or RDMA. If RDMA support is required, set ``beegfs_rdma_support`` should be set to true. Also, OFED should be installed on all target nodes.
    * For BeeGFS communication happening over RDMA, the ``beegfs_mgmt_server`` should be provided with the Infiniband IP of the management server.



