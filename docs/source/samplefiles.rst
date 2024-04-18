Sample Files
=============

inventory file
-----------------

.. caution:: All the file contents mentioned below are case sensitive.

::

        #Batch Scheduler: Slurm

        [slurm_control_node]

        10.5.1.101

        [slurm_node]

        10.5.1.103

        10.5.1.104

        [login]

        10.5.1.105



        #General Cluster Storage

        [auth_server]

        10.5.1.106

        #AI Scheduler: Kubernetes

        [kube_control_plane]

        10.5.1.101

        [etcd]

        10.5.1.101

        [kube_node]

        10.5.1.102

        10.5.1.103

        10.5.1.104

        10.5.1.105

        10.5.1.106

.. note:: The auth_server is common to both slurm and kubernetes clusters.


inventory file to delete node from the cluster
-------------------------------------------------

::

    [nodes]
    10.5.0.33

pxe_mapping_file.csv
------------------------------------

::

    SERVICE_TAG,HOSTNAME,ADMIN_MAC,ADMIN_IP,BMC_IP
    XXXXXXX,n1,xx:yy:zz:aa:bb:cc,10.5.0.101,10.3.0.101
    XXXXXXX,n2,aa:bb:cc:dd:ee:ff,10.5.0.102,10.3.0.102


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




