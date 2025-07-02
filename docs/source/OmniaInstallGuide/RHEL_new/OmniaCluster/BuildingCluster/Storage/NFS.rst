NFS
=====

Network File System (NFS) is a networking protocol for distributed file sharing. A file system defines the way data in the form of files is stored and retrieved from storage devices, such as hard disk drives, solid-state drives and tape drives. NFS is a network file sharing protocol that defines the way files are stored and retrieved from storage devices across networks.

.. note:: NFS is a mandatory feature for all clusters set up by Omnia. Omnia sets up the NFS server and mounts the NFS client when ``nfs_server`` value is true.

**Prerequisites**

* NFS is set up on Omnia clusters based on the inputs provided in ``input/storage_config.yml``.

    +-----------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | Parameter             | Details                                                                                                                                                     |
    +=======================+=============================================================================================================================================================+
    | **nfs_client_params** | * This JSON list contains all parameters required to set up NFS.                                                                                            |
    |                       | * For a bolt-on set up where there is a pre-existing NFS server, set ``nfs_server`` to ``false``.                                                           |
    |      ``JSON List``    | * When ``nfs_server`` is set to ``true``, an NFS share is created on a server IP in the cluster for access by all other cluster nodes.                      |
    |                       | * Ensure that the value of ``share_path`` in ``input/omnia_config.yml`` matches at least one of the ``client_share_path`` values in the JSON list provided. |
    |      Required         |                                                                                                                                                             |
    +-----------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+


    .. image:: ../../../../../images/nfs_flowchart.png



    * The fields listed in ``nfs_client_params`` are:

      - **server_ip**: IP of the intended NFS server. To set up an NFS server on the OIM, use the value ``localhost``. Use an IP  address to configure access anywhere else.

      - **server_share_path**: Folder on which the NFS server mounted.

      - **client_share_path**: Target directory for the NFS mount on the client. If left empty, the respective ``server_share_path value`` will be taken for ``client_share_path``.

      - **nfs_server**: Indicates whether an external NFS server is available (``false``) or an NFS server will need to be created (``true``).

      - **client_mount_options**: Indicates the NFS share mount options.

      - **slurm_share**: Indicates that the target cluster uses Slurm.

      - **k8s_share**: Indicates that the target cluster uses Kubernetes.

     .. note:: To install any benchmarking software like UCX or OpenMPI, ``slurm_share`` or ``k8s_share`` must be set to true. If both are set to true, a higher precedence is given to ``slurm_share``.

  To configure all cluster nodes to access a single external NFS server export, use the below sample: ::

         - { server_ip: 10.5.0.101, server_share_path: "/mnt/share", client_share_path: "/home", client_mount_options: "nosuid,rw,sync,hard", nfs_server: true, slurm_share: true, k8s_share: true }

  To configure the cluster nodes to access a new NFS server on the OIM as well as an external NFS server, use the below example: ::

        - { server_ip: localhost, server_share_path: "/mnt/share1", client_share_path: "/home", client_mount_options: "nosuid,rw,sync,hard", nfs_server: true, slurm_share: true, k8s_share: true }
        - { server_ip: 198.168.0.1, server_share_path: "/mnt/share2", client_share_path: "/mnt/mount2", client_mount_options: "nosuid,rw,sync,hard", nfs_server: false, slurm_share: true, k8s_share: true }

  To configure the cluster nodes to access new NFS server exports on the cluster nodes, use the below sample: ::

        - { server_ip: 198.168.0.1, server_share_path: "/mnt/share1", client_share_path: "/mnt/mount1", client_mount_options: "nosuid,rw,sync,hard", nfs_server: false, slurm_share: true, k8s_share: true }
        - { server_ip: 198.168.0.2, server_share_path: "/mnt/share2", client_share_path: "/mnt/mount2", client_mount_options: "nosuid,rw,sync,hard", nfs_server: false, slurm_share: true, k8s_share: true }


* Ensure that an NFS local repository is created by including ``{"name": "nfs"},`` in ``input/software_config.json``. For more information, `click here <../../../CreateLocalRepo/index.html>`_.
* If the intended cluster will run Slurm, set the value of ``slurm_installation_type`` in ``input/omnia_config.yml`` to ``nfs_share``.
* If an external NFS share is used, make sure that ``/etc/exports`` on the NFS server is populated with the same paths listed as ``server_share_path`` in the ``nfs_client_params`` in ``input/storage_config.yml``.
* Omnia supports all NFS mount options. Without user input, the default mount options are ``nosuid,rw,sync,hard,intr``.


**Running the playbook**

Run the ``storage.yml`` playbook : ::

    cd storage
    ansible-playbook storage.yml -i inventory

Use the linked `inventory file <../../../../samplefiles.html#inventory-file>`_ for the above playbook.


Post configuration, enable the following services (using this command: ``firewall-cmd --permanent --add-service=<service name>``) and then reload the firewall (using this command: ``firewall-cmd --reload``).

  - nfs

  - rpc-bind

  - mountd

.. caution::
   *  After an NFS client is configured, if the NFS server is rebooted, the client may not be able to reach the server. In those cases, restart the NFS services on the server using the below command:

        ::

            systemctl disable nfs-server
            systemctl enable nfs-server
            systemctl restart nfs-server

   * When ``nfs_server`` is false, enable the following services after configuration using this command: ``firewall-cmd --permanent --add-service=<service name>``) and then reload the firewall (using this command: ``firewall-cmd --reload``).

       - nfs

       - rpc-bind

       - mountd

