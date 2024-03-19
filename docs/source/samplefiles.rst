Sample Files
=============

inventory file
-----------------

.. caution:: All the file contents mentioned below are case sensitive.

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

        [kube_node]

        # node2

        # node3

        # node4

        # node5

        # node6



pxe_mapping_file.csv
------------------------------------

::

    SERVICE_TAG,HOSTNAME,ADMIN_MAC,ADMIN_IP,BMC_IP
    6XCVT4,n1,xx:yy:zz:aa:bb:cc,10.5.0.101,10.3.0.101
    V345H5,n2,aa:bb:cc:dd:ee:ff,10.5.0.102,10.3.0.102


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




