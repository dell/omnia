Sample Files
=============

inventory file
-----------------


::

    [manager]
    10.5.0.101

    [compute]
    10.5.0.102
    10.5.0.103

    [login]
    10.5.0.104


pxe_mapping_file.csv
------------------------------------

::

    MAC,Hostname,IP

    xx:yy:zz:aa:bb:cc,server,10.5.0.101

    aa:bb:cc:dd:ee:ff,server2, 10.5.0.102

.. note:: To skip the provisioning of a particular node in the list, simply append a '#' to the beginning of the line pertaining to that node.

switch_inventory
------------------
::

    10.3.0.101
    10.3.0.102


powervault_inventory
------------------
::

    10.3.0.105




NFS Server inventory file
-------------------------


::

    [nfs]
    10.5.0.104




