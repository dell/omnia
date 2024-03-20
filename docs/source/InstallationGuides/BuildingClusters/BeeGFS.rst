BeeGFS bolt on
--------------

BeeGFS is a hardware-independent POSIX parallel file system (a.k.a. Software-defined Parallel Storage) developed with a strong focus on performance and designed for ease of use, simple installation, and management.

.. image:: ../../images/BeeGFS_Structure.jpg


**Pre Requisites before installing BeeGFS client**

* Ensure that the BeeGFS server is set up using the `linked steps <../../Appendices/BeeGFSServer.html>`_.
* Ensure that a ``connAuthFile`` is configured on the server as explained `here <../../Appendices/BeeGFSServer.html>`_

.. caution:: Configuring a ``connAuthFile`` is now mandatory. Services will no longer start if a ``connAuthFile`` is not configured

* Ensure that the following ports are open for TCP and UDP connectivity:

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



* Nodes provisioned using the Omnia provision tool do not require a RedHat subscription to set up BeeGFS on RHEL cluster nodes.

* For RHEL cluster nodes not provisioned by Omnia, ensure that RedHat subscription is enabled on all cluster nodes. Every cluster node will require a RedHat subscription.

.. note:: BeeGFS services over RDMA is only supported on RHEL 8.3 and above due to limitations on BeeGFS. When setting up your cluster with RDMA support, check the BeeGFS documentation to provide appropriate values in ``input/storage_config.yml``.

* If the cluster runs Rocky, ensure that versions running are compatible by checking our `support matrix <../../Overview/SupportMatrix/OperatingSystems/Rocky.html>`_.

**Installing the BeeGFS client via Omnia**


After the required parameters are filled in ``input/storage_config.yml``, Omnia installs BeeGFS on all nodes while executing the ``storage.yml`` playbook.

.. caution:: Do not remove or comment any lines in the ``input/storage_config.yml`` file.

.. csv-table:: Parameters for storage
   :file: ../../Tables/storage_config.csv
   :header-rows: 1
   :keepspace:

.. note::
    * BeeGFS client-server communication can take place over TCP or RDMA. If RDMA support is required, set ``beegfs_rdma_support`` should be set to true. Also, OFED should be installed on all cluster nodes.
    * For BeeGFS communication happening over RDMA, the ``beegfs_mgmt_server`` should be provided with the Infiniband IP of the management server.
    * The parameter inventory refers to the `inventory file <../../samplefiles.html>`_ listing all relevant nodes.)

If ``input/storage_config.yml`` is populated before running ``omnia.yml``, BeeGFS client will be set up during the run of ``omnia.yml``.

If ``omnia.yml`` is not leveraged to set up BeeGFS, run the ``storage.yml`` playbook : ::

    cd storage
    ansible-playbook storage.yml -i inventory


.. note:: Once BeeGFS is successfully set up, set ``enable_omnia_nfs`` (``input/omnia_config.yml``) to false and  ``omnia_usrhome_share`` (``input/omnia_config.yml``) to an accessible share path in BeeGFS to use the path across the cluster for deployments.