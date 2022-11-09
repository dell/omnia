BeeGFS Bolt On
================

BeeGFS is a hardware-independent POSIX parallel file system (a.k.a. Software-defined Parallel Storage) developed with a strong focus on performance and designed for ease of use, simple installation, and management. BeeGFS is created on an Available Source development model (source code is publicly available), offering a self-supported Community Edition and a fully supported Enterprise Edition with additional features and functionalities. BeeGFS is designed for all performance-oriented environments including HPC, AI and Deep Learning, Media & Entertainment, Life Sciences, and Oil & Gas (to name a few).

.. image:: ../../images/BeeGFS_Structure.jpg


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



* Ensure that the nodes in the inventory have been assigned roles: manager, compute, login_node (optional), nfs_node

* If the cluster runs RHEL, ensure that versions running are compatible:

+------------+--------------------------------+-----------------+
| OS version | BeeGFS Client Version          | Status          |
+============+================================+=================+
| RHEL-8.0   | 7.2                            | Supported       |
+------------+--------------------------------+-----------------+
| RHEL-8.0   | 7.2.6                          | Supported       |
+------------+--------------------------------+-----------------+
| RHEL-8.3   | 7.2                            | Not   Supported |
+------------+--------------------------------+-----------------+
| RHEL-8.3   | 7.2.1                          | Supported       |
+------------+--------------------------------+-----------------+
| RHEL-8.3   | 7.2.4                          | Supported       |
+------------+--------------------------------+-----------------+
| RHEL-8.3   | 7.2.1                          | Supported       |
+------------+--------------------------------+-----------------+
| RHEL-8.3   | 7.2.2                          | Supported       |
+------------+--------------------------------+-----------------+
| RHEL-8.3   | 7.2.5                          | Supported       |
+------------+--------------------------------+-----------------+
| RHEL-8.3   | 7.2.6                          | Supported       |
+------------+--------------------------------+-----------------+
| RHEL-8.3   | 7.3.0 upgrading from 7.2.x/7.2 | Not Supported   |
+------------+--------------------------------+-----------------+
| RHEL-8.3   | 7.x client ,   7.y mgmtd       | Not   Supported |
+------------+--------------------------------+-----------------+
| RHEL-8.3   | 7.2.6                          | Supported       |
+------------+--------------------------------+-----------------+
| RHEL-8.3   | 7.2.6                          | Supported       |
+------------+--------------------------------+-----------------+
| RHEL-8.3   | 7.3.0                          | Supported       |
+------------+--------------------------------+-----------------+


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



