Create an inventory file from the list of provisioned nodes
===============================================================

* Go to /opt/omnia/omnia_inventory/ and view the provisioned nodes.
* Create a separate inventory file with your choice of nodes to build a k8s cluster. For example, ::

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

.. image:: ../../images/Visio/Create_inventory.png
    :width: 600pt