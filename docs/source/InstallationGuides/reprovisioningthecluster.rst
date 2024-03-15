Re-provisioning the cluster
++++++++++++++++++++++++++++

**Pre-requisites**

    * Run the `delete node playbook. <deletenode.html#delete-node-from-the-cluster>`_ for every target node.

In the event that an existing Omnia cluster needs a different OS version or a fresh installation, the cluster can be re-provisioned.

If a re-deployment with no modifications are required  ::

    ansible-playbook discovery_provision.yml -i inventory


Where the inventory contains a list of host IPs (Sourced from the `nodeinfo table <InstallingProvisionTool/ViewingDB.html>`_) as shown below:

::

    10.5.0.101
    10.5.0.102


.. note::
    * The host IPs passed in the inventory should be assigned by Omnia. They will not be changed during the re-provisioning.
    * If the nodes were discovered via mapping, manually reboot target nodes.
    * Do not include groups like *manager*, *compute* and *login* in the passed inventory.

**Setting up the cluster**

1. Insert the new IPs (only if a new node is to be added) and/or move nodes between groups in the existing inventory file following the below example.

*Existing inventory*

::

    [kube_control_plane]
    10.5.0.101

    [kube_node]
    10.5.0.102
    10.5.0.103

    [login]
    10.5.0.104

*Updated inventory with the new node information*

::

    [kube_control_plane]
    10.5.0.102

    [kube_node]
    10.5.0.101
    10.5.0.103
    10.5.0.104
    10.5.0.106

    [login]
    10.5.0.105

In the above example, the compute node: 10.5.0.102 has been moved to manager, a new login node: 10.5.0.105 has been set up, and the node: 10.5.0.106 has been added to the cluster as a compute node.

.. note:: To change the configuration of the cluster, the files ``input/omnia_config.yml``, ``input/security_config.yml`` and ``input/storage_config.yml`` can be updated before running ``omnia.yml``.

3. To install `security <BuildingClusters/Authentication.html>`_, `job scheduler <BuildingClusters/installscheduler.html>`_ and storage tools (`NFS <BuildingClusters/NFS.html>`_, `BeeGFS <BuildingClusters/BeeGFS.html>`_) on the node, run ``omnia.yml``: ::

    ansible-playbook omnia.yml -i inventory



