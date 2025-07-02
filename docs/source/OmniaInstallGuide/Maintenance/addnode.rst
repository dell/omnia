Adding new nodes
==================

**Provisioning the new node**

A new node can be provisioned using the following ways, based on the `discovery mechanism <../RHEL_new/Provision/DiscoveryMechanisms/index.html>`_ used:

1. Using a **mapping file**:

    * Update the existing mapping file by appending the new entry (without the disrupting the older entries) or provide a new mapping file by pointing ``pxe_mapping_file_path`` in ``provision_config.yml`` to the new location.

    .. note:: Any IP overlap between the mapping files will result in PXE boot failure. This can be resolved by running the `Delete Node script <deletenode.html>`_ or the `Clean Up script <cleanup.html>`_. Re-run ``discovery_provision.yml`` once the node has been deleted.

    * Run ``discovery_provision.yml`` ::

        ansible-playbook discovery_provision.yml

    *  Manually PXE boot the target servers after the ``discovery_provision.yml`` playbook (if ``bmc_ip`` is not provided in the mapping file) is executed and the target node lists as **booted** in the `nodeinfo table <../RHEL_new/Provision/ViewingDB.html>`_.



2. Using **BMC** method:

    * Update ``discover_ranges`` under ``bmc_network`` in ``input/network_spec.yml`` with the desired range of IPs to be discovered. For more information, `click here <../RHEL_new/Provision/provisionparams.html#id6>`_.
    * Run ``discovery_provision.yml`` ::

        ansible-playbook discovery_provision.yml



3. Using **switch-based** method:

    * Edit or append JSON list stored in ``switch_based_details`` in ``input/provision_config.yml``.

    .. note::
        * All ports residing on the same switch should be listed in the same JSON list element.
        * Ports configured via Omnia should be not be removed from ``switch_based_details`` in ``input/provision_config.yml``.


    * Run ``discovery_provision.yml`` ::


        ansible-playbook discovery_provision.yml

    * Manually PXE boot the target servers after the ``discovery_provision.yml`` playbook is executed and the target node lists as **booted** in the `nodeinfo table <../RHEL_new/Provision/ViewingDB.html>`_.


Verify that the node has been provisioned successfully by checking the Omnia `nodeinfo table <../RHEL_new/Provision/ViewingDB.html>`_.

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
    * The ``[etcd]`` group only supports an odd number of servers in the group. Adding nodes to ``[etcd]`` groups is not supported in re-run scenarios.
    * Do not change the ``kube_control_plane``, ``slurm_control_node`` and/or ``auth_server`` in the existing inventory file. Simply add the new node information in the ``kube_node`` and/or ``slurm_node`` group.
    * When re-running ``omnia.yml`` to add a new node, ensure that the ``input/security_config.yml`` and ``input/omnia_config.yml`` are not edited between runs.

2. Once the new node IPs have been provided in the inventory, you can install security tools (OpenLDAP, FreeIPA), job schedulers (Kubernetes, Slurm), and storage tools (NFS, BeeGFS) on the nodes by executing ``omnia.yml`` with the updated inventory file: ::

    ansible-playbook omnia.yml -i inventory



