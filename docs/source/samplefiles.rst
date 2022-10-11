Sample Files
=============

device_ip_list.yml
-------------------


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

mapping_device_file.csv
-----------------------

::

    MAC,IP
    xx:yy:zz:aa:bb,1.2.3.4

host_mapping_file_os_provisioning.csv
------------------------------------

::


    MAC,Hostname,IP

    xx:yy:zz:aa:bb,server,1.2.3.4

    aa:bb:cc:dd:ee,server2,10.10.11.12


host_mapping_file_one_touch.csv
-------------------------------

::


        MAC,Hostname,IP,Component_role

        xx:yy:zz:aa:bb,server,1.2.3.4,manager

        aa:bb:cc:dd:ee,server2,10.10.11.12,nfs_node






