Sample Files
=============

.. caution:: All the file contents mentioned below are case sensitive.

inventory file
-----------------


::

        #Batch Scheduler: Slurm

        [slurm_control_node]

        # node1

        [slurmdbd]

        #node2

        [slurm_node]

        #node3

        #node4

        [login]

        #node5



        #General Cluster Storage

        #NFS node

        [nfs]

        #node10



        [auth_server]

        #node12

        #AI Scheduler: Kubernetes

        [kube_control_plane]

        # node1

        [etcd]

        # node1

        # node2in

        # node3



        [kube_node]

        # node2

        # node3

        # node4

        # node5

        # node6



        [calico_rr]

        #node7


pxe_mapping_file.csv
------------------------------------

::

    MAC,Hostname,IP

    xx:yy:zz:aa:bb:cc,server,10.5.0.101

    aa:bb:cc:dd:ee:ff,server2, 10.5.0.102

.. note::
    * To skip the provisioning of a particular node in the list, simply append a '#' to the beginning of the line pertaining to that node.
    * Hostnames listed in this file should be exclusively lower-case with no special characters.


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

    #General Cluster Storage
    #NFS node
    [nfs]
    #node10




