NFS Bolt On
------------

* Ensure that an external NFS server is running. NFS clients are mounted using the external NFS server's IP.

* Fill out the ``nfs_client_params`` variable in the ``input/storage_config.yml`` file in JSON format using the samples provided below.

* This role runs on manager, compute and login nodes.

* Make sure that ``/etc/exports`` on the NFS server is populated with the same paths listed as ``server_share_path`` in the ``nfs_client_params`` in ``input/storage_config.yml``.

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

        - { server_ip: 10.5.0.101, server_share_path: "/mnt/share", client_share_path: "/mnt/client", client_mount_options: "nosuid,rw,sync,hard,intr" }

  2. **Multiple Mount NFS Filesystem**: Multiple filesystems are mounted from a single NFS server. The value of ``nfs_client_params`` would be::

        - { server_ip: 10.5.0.101, server_share_path: "/mnt/share1", client_share_path: "/mnt/client1", client_mount_options: "nosuid,rw,sync,hard,intr" }
        - { server_ip: 10.5.0.101, server_share_path: "/mnt/share2", client_share_path: "/mnt/client2", client_mount_options: "nosuid,rw,sync,hard,intr" }

   3. **Multiple NFS Filesystems**: Multiple filesystems are mounted from multiple NFS servers. The value of ``nfs_client_params`` would be::

        - { server_ip: 10.5.0.101, server_share_path: "/mnt/server1", client_share_path: "/mnt/client1", client_mount_options: "nosuid,rw,sync,hard,intr" }
        - { server_ip: 10.5.0.102, server_share_path: "/mnt/server2", client_share_path: "/mnt/client2", client_mount_options: "nosuid,rw,sync,hard,intr" }
        - { server_ip: 10.5.0.103, server_share_path: "/mnt/server3", client_share_path: "/mnt/client3", client_mount_options: "nosuid,rw,sync,hard,intr" }



.. warning::
    After an NFS client is configured, if the NFS server is rebooted, the client may not be able to reach the server. In those cases, restart the NFS services on the server using the below command:

        ::

            systemctl disable nfs-server
            systemctl enable nfs-server
            systemctl restart nfs-server



