Adding new nodes
++++++++++++++++++

**Provisioning the new node**

A new node can be added using the following ways:

* If ``pxe_mapping_file_path`` is provided in ``input/provision_config.yml```:

    * Update the existing mapping file by appending the new entry (without the disrupting the older entries) or provide a new mapping file by pointing ``pxe_mapping_file_path`` in ``provision_config.yml`` to the new location.

    .. note:: When re-running ``discovery_provision.yml`` with a new mapping file, ensure that existing IPs from the current mapping file are not provided in the new mapping file. Any IP overlap between mapping files will result in PXE failure. This can only be resolved by running `the Clean Up script <CleanUpScript.html>`_ followed by ``discovery_provision.yml``.

    * Run ``discovery_provision.yml``.::

        ansible-playbook discovery_provision.yml

    *  Manually PXE boot the target servers after the ``discovery_provision.yml`` playbook (if ``bmc_ip`` is not provided in the mapping file) is executed and the target node lists as **booted** `in the nodeinfo table <InstallingProvisionTool/ViewingDB.html>`_


* When target nodes were discovered using BMC:

    * Run ``discovery_provision.yml`` once the node has joined the cluster using an IP that exists within the provided range. ::


        ansible-playbook discovery_provision.yml

* When target nodes were discovered using ``switch_based_details`` in ``input/provision_config.yml``:

    * Edit or append JSON list stored in ``switch_based_details`` in ``input/provision_config.yml``.

    .. note::
        * All ports residing on the same switch should be listed in the same JSON list element.
        * Ports configured via Omnia should be not be removed from ``switch_based_details`` in ``input/provision_config.yml``.


    * Run ``discovery_provision.yml``. ::


        ansible-playbook discovery_provision.yml

    * Manually PXE boot the target servers after the ``discovery_provision.yml`` playbook is executed and the target node lists as **booted** `in the nodeinfo table <InstallingProvsionTool/ViewingDB.html>`_


Verify that the node has been provisioned successfully by `checking the Omnia nodeinfo table. <InstallingProvisionTool/ViewingDB.html>`_

**Adding new compute nodes to the cluster**

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

    # node1



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

    # node1


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
    * The ``[etcd]`` group only supports an odd number of servers in the group.
    * Do not change the kube_control_plane/slurm_control_node/auth_server in the existing inventory. Simply add the new node information in the kube_node/slurm_node group.
    * When re-running ``omnia.yml`` to add a new node, ensure that the ``input/security_config.yml`` and ``input/omnia_config.yml`` are not edited between runs.

3. To install `security <BuildingClusters/Authentication.html>`_, `job scheduler <BuildingClusters/installscheduler.html>`_ and storage tools (`NFS <BuildingClusters/NFS.html>`_, `BeeGFS <BuildingClusters/BeeGFS.html>`_) on the node, run ``omnia.yml``: ::

    ansible-playbook omnia.yml -i inventory



