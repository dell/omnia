Re-provisioning the cluster
++++++++++++++++++++++++++++

**Pre-requisites**

    * Run the `delete node playbook. <deletenode.html#delete-node-from-the-cluster>`_ for every target node.

In the event that an existing Omnia cluster needs a different OS version or a fresh installation, the cluster can be re-provisioned.

If a re-deployment with no modifications are required  ::

    ansible-playbook discovery_provision.yml

**Setting up the cluster**

1. Insert the new IPs in the existing inventory file following the below example.

*Existing kubernetes inventory*

::

    [kube_control_plane]
    10.5.0.101

    [kube_node]
    10.5.0.102
    10.5.0.103

    [auth_server]
    10.5.0.101

    [etcd]
    10.5.0.110



*Updated kubernetes inventory with the new node information*

::

    [kube_control_plane]
    10.5.0.101

    [kube_node]
    10.5.0.102
    10.5.0.103
    10.5.0.105
    10.5.0.106

    [auth_server]
    10.5.0.101

    [etcd]
    10.5.0.110

*Existing Slurm inventory*

::

    [slurm_control_node]
    10.5.0.101

    [slurm_node]
    10.5.0.102
    10.5.0.103

    [login]
    10.5.0.104

    [auth_server]
    10.5.0.101


*Updated Slurm inventory with the new node information*

::

    [slurm_control_node]
    10.5.0.101

    [slurm_node]
    10.5.0.102
    10.5.0.103
    10.5.0.105
    10.5.0.106

    [login]
    10.5.0.104

    [auth_server]
    10.5.0.101



In the above examples, nodes 10.5.0.105 and 10.5.0.106 have been added to the cluster as compute nodes.

.. note::
    * Do not change the kube_control_plane/slurm_control_node/auth_server in the existing inventory. Simply add the new node information in the kube_node/slurm_node group.
    * When re-running ``omnia.yml`` to add a new node, ensure that the ``input/security_config.yml`` and ``input/omnia_config.yml`` are not edited between runs.

3. To install `security <BuildingClusters/Authentication.html>`_, `job scheduler <BuildingClusters/installscheduler.html>`_ and storage tools (`NFS <BuildingClusters/NFS.html>`_, `BeeGFS <BuildingClusters/BeeGFS.html>`_) on the node, run ``omnia.yml``: ::

    ansible-playbook omnia.yml -i inventory



