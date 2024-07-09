Shared and distributed storage deployment
============================================

The storage role allows users to configure PowerVault Storage devices, BeeGFS and NFS services on the cluster.

1. Enter all required parameters in ``input/storage_config.yml``

.. csv-table:: Parameters for Storage
   :file: ../../Tables/storage_config.csv
   :header-rows: 1
   :keepspace:

.. note:: If ``storage.yml`` is run with the ``input/storage_config.yml`` filled out, BeeGFS and NFS client will be set up.

2. Ensure that the entry ``{"name": "beegfs", "version": "7.2.6"},`` is included in ``input/software_config.json`` and a local repository is created. For more information, `click here. <../../InstallationGuides/LocalRepo/index.html>`_

**Installing BeeGFS Client**

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

    * When working with RHEL, ensure that the BeeGFS configuration is supported using the `link here <../../Overview/SupportMatrix/OperatingSystems/RedHat.html>`_.

    * If the BeeGFS server (MGMTD, Meta, or storage) is running BeeGFS version 7.3.1 or higher, the security feature on the server should be disabled. Change the value of ``connDisableAuthentication`` to ``true`` in /etc/beegfs/beegfs-mgmtd.conf, /etc/beegfs/beegfs-meta.conf and /etc/beegfs/beegfs-storage.conf. Restart the services to complete the task: ::

        systemctl restart beegfs-mgmtd
        systemctl restart beegfs-meta
        systemctl restart beegfs-storage
        systemctl status beegfs-mgmtd
        systemctl status beegfs-meta
        systemctl status beegfs-storage


**NFS bolt-on**

* Ensure that an external NFS server is running. NFS clients are mounted using the external NFS server's IP.

* Fill out the ``nfs_client_params`` variable in the ``storage_config.yml`` file in JSON format using the samples provided above.

* This role runs on manager, compute and login nodes.

* Ensure that ``/etc/exports`` on the NFS server is populated with the same paths listed as ``server_share_path`` in the ``nfs_client_params`` in ``omnia_config.yml``.

* Post configuration, enable the following services (using this command: ``firewall-cmd --permanent --add-service=<service name>``) and then reload the firewall (using this command: ``firewall-cmd --reload``).

  - nfs

  - rpc-bind

  - mountd

* Omnia supports all NFS mount options. Without user input, the default mount options are nosuid,rw,sync,hard,intr. For a list of mount options, `click here <https://linux.die.net/man/5/nfs>`_.

* The fields listed in ``nfs_client_params`` are:

  - server_ip: IP of NFS server

  - server_share_path: Folder on which NFS server mounted

  - client_share_path: Target directory for the NFS mount on the client. If left empty, respective ``server_share_path value`` will be taken for ``client_share_path``.

  - client_mount_options: The mount options when mounting the NFS export on the client. Default value: nosuid,rw,sync,hard,intr.



* There are 3 ways to configure the feature:

  1. **Single NFS node** : A single NFS filesystem is mounted from a single NFS server. The value of ``nfs_client_params`` would be::

        - { server_ip: xx.xx.xx.xx, server_share_path: "/mnt/share", client_share_path: "/mnt/client", client_mount_options: "nosuid,rw,sync,hard,intr" }

  2. **Multiple Mount NFS Filesystem**: Multiple filesystems are mounted from a single NFS server. The value of ``nfs_client_params`` would be::

        - { server_ip: xx.xx.xx.xx, server_share_path: "/mnt/server1", client_share_path: "/mnt/client1", client_mount_options: "nosuid,rw,sync,hard,intr" }
        - { server_ip: xx.xx.xx.xx, server_share_path: "/mnt/server2", client_share_path: "/mnt/client2", client_mount_options: "nosuid,rw,sync,hard,intr" }

   3. **Multiple NFS Filesystems**: Multiple filesystems are mounted from multiple NFS servers. The value of ``nfs_client_params`` would be::

        - { server_ip: xx.xx.xx.xx, server_share_path: "/mnt/server1", client_share_path: "/mnt/client1", client_mount_options: "nosuid,rw,sync,hard,intr" }
        - { server_ip: yy.yy.yy.yy, server_share_path: "/mnt/server2", client_share_path: "/mnt/client2", client_mount_options: "nosuid,rw,sync,hard,intr" }
        - { server_ip: zz.zz.zz.zz, server_share_path: "/mnt/server3", client_share_path: "/mnt/client3", client_mount_options: "nosuid,rw,sync,hard,intr" }



**To run the playbook:** ::

    cd omnia/storage
    ansible-playbook storage.yml -i inventory

(Where inventory refers to the `inventory file <../../samplefiles.html>`_ listing kube_control_plane, login_node and compute nodes.)

.. note::  If a subsequent run of ``storage.yml`` fails, the ``storage_config.yml`` file will be unencrypted.

