Sample Files
=============

device_ip_list.yml
------------------
::

    172.19.0.100
    172.19.0.200


host_inventory_file
--------------------


::

    all:
      children:
        manager:
          hosts:
            manager.omnia.local:
        nfs_node:
          hosts:
            storage.omnia.local:
        login_node:
          hosts:
            login1.omnia.local:
        compute:
          hosts:
            compute[001:004].omnia.local:
            compute010.omnia.local:
            compute011.omnia.local:

host_inventory_file.ini
------------------------


::

    [manager]
    manager.omnia.local

    [nfs_node]
    manager.omnia.local

    [login_node]
    login1.omnia.local

    [compute]
    compute[000:064]



pxe_mapping_file.csv
------------------------------------

::

    MAC,Hostname,IP

    xx:yy:zz:aa:bb:cc,server,172.29.0.5

    aa:bb:cc:dd:ee:ff,server2, 172.29.0.6








