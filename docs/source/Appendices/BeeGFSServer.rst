Setting up the BeeGFS server
-----------------------------

1. Download and install the required BeeGFS version using the below command: ::

    wget -O /etc/yum.repos.d/beegfs_rhel8.repo https://www.beegfs.io/release/beegfs_7.3.2/dists/beegfs-rhel8.repo

    yum install beegfs-mgmtd -y beegfs-meta libbeegfs-ib beegfs-storage -y

.. note:: These steps can safely be used on Rocky and RHEL servers.

2. Create a directory for BeeGFS storage configuration: ::

    mkdir /root/test_beegfs


3. Create an authentication file used by BeeGFS versions >= 7.2.7: ::

    dd if=/dev/random of=/etc/beegfs/connauthfile bs=128 count=1

4. Setup the BeeGFS services:
    - Manager: ``/opt/beegfs/sbin/beegfs-setup-mgmtd -p /data/beegfs/beegfs_mgmtd``
    - Meta: ``/opt/beegfs/sbin/beegfs-setup-meta -p /data/beegfs/beegfs_meta -s 2 -m <beegfs_server_IP>``
    - Storage: ``/opt/beegfs/sbin/beegfs-setup-storage -p /root/test_beegfs -s 3 -i 301 -m <beegfs_server_IP>``
5. Append ``connAuthFile = /etc/beegfs/connauthfile`` in the following files:

   _ ``/etc/beegfs/beegfs-mgmtd.conf``

   _ ``/etc/beegfs/beegfs-storage.conf``

   _ ``/etc/beegfs/beegfs-meta.conf``

6. Start BeeGFS services by running the following commands:
    - Manager: ``systemctl start beegfs-mgmtd``
    - Meta: ``systemctl start beegfs-meta``
    - Storage: ``systemctl start beegfs-storage``


