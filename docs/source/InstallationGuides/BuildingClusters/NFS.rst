NFS
____

Network File System (NFS) is a networking protocol for distributed file sharing. A file system defines the way data in the form of files is stored and retrieved from storage devices, such as hard disk drives, solid-state drives and tape drives. NFS is a network file sharing protocol that defines the way files are stored and retrieved from storage devices across networks. NFS is a mandatory feature for all clusters set up by Omnia.


**Pre requisites**

* NFS is set up on Omnia clusters based on the inputs provided in ``input/storage_config.yml``.

    .. csv-table:: Parameters for Storage configuration
       :file: ../../Tables/storage_config.csv
       :header-rows: 1
       :keepspace:
       :class: longtable


    .. image:: ../../images/NFS_FlowChart.png

    * The fields listed in ``nfs_client_params`` are:

      - server_ip: IP of the intended NFS server. To set up an NFS server on the control plane, use the value ``localhost``.

      - server_share_path: Folder on which the NFS server mounted.

      - client_share_path: Target directory for the NFS mount on the client. If left empty, the respective ``server_share_path value`` will be taken for ``client_share_path``.

      - client_mount_options: The mount options when mounting the NFS export on the client. Default value: nosuid,rw,sync,hard,intr. For a list of mount options, `click here <https://man7.org/linux/man-pages/man8/mount.8.html>`_.

      - nfs_server: Indicates whether an external NFS server is available (true) or an NFS export will need to be created (false).

  To configure all cluster nodes to access a single external NFS server export, use the below sample: ::

         - { server_ip: 10.5.0.101, server_share_path: "/mnt/share", client_share_path: "/home", client_mount_options: "nosuid,rw,sync,hard", nfs_server: true }

  To configure the cluster nodes to access a new NFS server on the control plane as well as an external NFS server, use the below example: ::

        - { server_ip: localhost, server_share_path: "/mnt/share1", client_share_path: "/home", client_mount_options: "nosuid,rw,sync,hard", nfs_server: true }
        - { server_ip: 198.168.0.1, server_share_path: "/mnt/share2", client_share_path: "/mnt/mount2", client_mount_options: "nosuid,rw,sync,hard", nfs_server: false }

  To configure the cluster nodes to access new NFS server exports on the cluster nodes, use the below sample: ::

        - { server_ip: 198.168.0.1, server_share_path: "/mnt/share1", client_share_path: "/mnt/mount1", client_mount_options: "nosuid,rw,sync,hard", nfs_server: false }
        - { server_ip: 198.168.0.2, server_share_path: "/mnt/share2", client_share_path: "/mnt/mount2", client_mount_options: "nosuid,rw,sync,hard", nfs_server: false }


* Ensure that an NFS local repository is created by including ``{"name": "nfs"},`` in ``input/software_config.json``. For more information, `click here. <../InstallationGuides/LocalRepo/index.html>`_
* Enter the value of ``share_path`` in ``input/omnia_config.yml``.

.. note:: Ensure that the value of ``share_path`` provided matches at least one value of ``client_share_path`` provided in ``nfs_client_params`` in ``input/storage_config.yml``.

* If an external NFS share is used, make sure that ``/etc/exports`` on the NFS server is populated with the same paths listed as ``server_share_path`` in the ``nfs_client_params`` in ``input/storage_config.yml``.
* Omnia supports all NFS mount options. Without user input, the default mount options are nosuid,rw,sync,hard,intr.


**Running the playbook**

If ``omnia.yml`` is not leveraged to set up NFS, run the ``storage.yml`` playbook : ::

    cd storage
    ansible-playbook storage.yml -i inventory


Post configuration, enable the following services (using this command: ``firewall-cmd --permanent --add-service=<service name>``) and then reload the firewall (using this command: ``firewall-cmd --reload``).

  - nfs

  - rpc-bind

  - mountd

.. caution::
    After an NFS client is configured, if the NFS server is rebooted, the client may not be able to reach the server. In those cases, restart the NFS services on the server using the below command:

        ::

            systemctl disable nfs-server
            systemctl enable nfs-server
            systemctl restart nfs-server


