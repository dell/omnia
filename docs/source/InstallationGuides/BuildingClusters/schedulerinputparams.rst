Input parameters for the cluster
-------------------------------------

These parameters are located in ``input/omnia_config.yml``, ``input/security_config.yml``, ``input/telemetry_config.yml`` and [optional] ``input/storage_config.yml``.

.. caution:: Do not remove or comment any lines in the ``input/omnia_config.yml``, ``input/security_config.yml`` and [optional] ``input/storage_config.yml`` file.

**omnia_config.yml**

.. csv-table:: Parameters for kubernetes
   :file: ../../Tables/scheduler_k8s.csv
   :header-rows: 1
   :keepspace:

.. csv-table:: Parameters for slurm setup
   :file: ../../Tables/scheduler_slurm.csv
   :header-rows: 1
   :keepspace:

**security_config.yml**

.. csv-table:: Parameters for FreeIPA
   :file: ../../Tables/security_config_freeipa.csv
   :header-rows: 1
   :keepspace:

.. csv-table:: Parameters for LDAP
   :file: ../../Tables/security_config_ldap.csv
   :header-rows: 1
   :keepspace:


**storage_config.yml**


+---------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Name                            | Details                                                                                                                                                                                                                                              |
+=================================+======================================================================================================================================================================================================================================================+
| nfs_client_params               | If NFS client services are to be deployed, enter the configuration   required here in JSON format. The server_ip provided should have an explicit   NFS server running.  If left blank, no   NFS configuration takes place. Possible values include: |
|      ``JSON list``              | 1. Single NFS file system: A single filesystem from a single NFS server is   mounted.                                                                                                                                                                |
|      Optional                   |                                                                                                                                                                                                                                                      |
|                                 | Sample value: ``- { server_ip: xx.xx.xx.xx, server_share_path:   “/mnt/share”, client_share_path: “/mnt/client”, client_mount_options:   “nosuid,rw,sync,hard,intr” }``                                                                              |
|                                 | 2. Multiple Mount NFS file system: Multiple filesystems from a single NFS   server are mounted.                                                                                                                                                      |
|                                 | Sample values:                                                                                                                                                                                                                                       |
|                                 |      ``- { server_ip: xx.xx.xx.xx, server_share_path: “/mnt/server1”,   client_share_path: “/mnt/client1”, client_mount_options:   “nosuid,rw,sync,hard,intr” }``                                                                                    |
|                                 |      ``- { server_ip: xx.xx.xx.xx, server_share_path: “/mnt/server2”,   client_share_path: “/mnt/client2”, client_mount_options:   “nosuid,rw,sync,hard,intr” }``                                                                                    |
|                                 | 3. Multiple NFS file systems: Multiple filesystems are mounted from   multiple servers.                                                                                                                                                              |
|                                 | Sample Values: ``- { server_ip: zz.zz.zz.zz, server_share_path:   “/mnt/share1”, client_share_path: “/mnt/client1”, client_mount_options:   “nosuid,rw,sync,hard,intr”}``                                                                            |
|                                 |      ``- { server_ip: xx.xx.xx.xx, server_share_path: “/mnt/share2”,   client_share_path: “/mnt/client2”, client_mount_options:   “nosuid,rw,sync,hard,intr”}``                                                                                      |
|                                 |      ``- { server_ip: yy.yy.yy.yy, server_share_path: “/mnt/share3”,   client_share_path: “/mnt/client3”, client_mount_options:   “nosuid,rw,sync,hard,intr”}``                                                                                      |
|                                 |                                                                                                                                                                                                                                                      |
|                                 |                                                                                                                                                                                                                                                      |
|                                 | **Default value**:  ``{ server_ip: ,   server_share_path: , client_share_path: , client_mount_options: }``                                                                                                                                           |
+---------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| beegfs_support                  | This variable is used to install beegfs-client on compute and manager   nodes                                                                                                                                                                        |
|      ``boolean``                |                                                                                                                                                                                                                                                      |
|      Optional                   | Choices:                                                                                                                                                                                                                                             |
|                                 |                                                                                                                                                                                                                                                      |
|                                 |      *  ``false`` <- Default                                                                                                                                                                                                                         |
|                                 |                                                                                                                                                                                                                                                      |
|                                 |      *  ``true``                                                                                                                                                                                                                                     |
+---------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| beegfs_rdma_support             | This variable is used if user has RDMA-capable network hardware (e.g.,   InfiniBand)                                                                                                                                                                 |
|      ``boolean``                |                                                                                                                                                                                                                                                      |
|      Optional                   | Choices:                                                                                                                                                                                                                                             |
|                                 |                                                                                                                                                                                                                                                      |
|                                 |      * ``false`` <- Default                                                                                                                                                                                                                          |
|                                 |                                                                                                                                                                                                                                                      |
|                                 |      * ``true``                                                                                                                                                                                                                                      |
+---------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| beegfs_ofed_kernel_modules_path | The path where separate OFED kernel modules are installed.                                                                                                                                                                                           |
|      ``string``                 |                                                                                                                                                                                                                                                      |
|      Optional                   |      **Default value**: ``"/usr/src/ofa_kernel/default/include"``                                                                                                                                                                                    |
+---------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| beegfs_mgmt_server              | BeeGFS management server IP. Note: The provided IP should have an   explicit BeeGFS management server running .                                                                                                                                      |
|      ``string``                 |                                                                                                                                                                                                                                                      |
|      Required                   |                                                                                                                                                                                                                                                      |
+---------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| beegfs_mounts                   | Beegfs-client file system mount location. If ``storage_yml`` is being   used to change the BeeGFS mounts location, set beegfs_unmount_client to   true                                                                                               |
|      ``string``                 |      **Default value**: "/mnt/beegfs"                                                                                                                                                                                                                |
|      Optional                   |                                                                                                                                                                                                                                                      |
+---------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| beegfs_unmount_client           | Changing this value to true will unmount running instance of BeeGFS   client and should only be used when decommisioning BeeGFS, changing the mount   location or changing the BeeGFS version.                                                       |
|      ``boolean``  [1]_          |                                                                                                                                                                                                                                                      |
|      Optional                   | Choices:                                                                                                                                                                                                                                             |
|                                 |                                                                                                                                                                                                                                                      |
|                                 |      * ``false`` <- Default                                                                                                                                                                                                                          |
|                                 |                                                                                                                                                                                                                                                      |
|                                 |      * ``true``                                                                                                                                                                                                                                      |
+---------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| beegfs_client_version           | Beegfs client version needed on compute and manager nodes.                                                                                                                                                                                           |
|      ``string``                 |                                                                                                                                                                                                                                                      |
|      Optional                   |      **Default value**: 7.2.6                                                                                                                                                                                                                        |
+---------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| beegfs_version_change           | Use this variable to change the BeeGFS version on the target nodes.                                                                                                                                                                                  |
|      ``boolean`` [1]_           |                                                                                                                                                                                                                                                      |
|      Optional                   | Choices:                                                                                                                                                                                                                                             |
|                                 |                                                                                                                                                                                                                                                      |
|                                 |      * ``false`` <- Default                                                                                                                                                                                                                          |
|                                 |                                                                                                                                                                                                                                                      |
|                                 |      * ``true``                                                                                                                                                                                                                                      |
+---------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| beegfs_secret_storage_filepath  | * The filepath (including the filename) where the ``connauthfile`` is   placed.                                                                                                                                                                      |
|      ``string``                 | * Required for Beegfs version >= 7.2.7                                                                                                                                                                                                               |
|      Required                   |                                                                                                                                                                                                                                                      |
|                                 |                                                                                                                                                                                                                                                      |
|                                 |      **Default values**: ``/home/connauthfile``                                                                                                                                                                                                      |
+---------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

**telemetry_config.yml**

.. csv-table:: Parameters
   :file: ../../Tables/telemetry_config.csv
   :header-rows: 1
   :keepspace:

.. [1] Boolean parameters do not need to be passed with double or single quotes.


Click here for more information on `FreeIPA, LDAP <Authentication.html>`_, `Telemetry <../../Roles/Telemetry/index.html>`_, `BeeGFS <BeeGFS.html>`_ or, `NFS <NFS.html>`_.

