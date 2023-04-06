Adding new nodes
+++++++++++++++++

While adding a new node to the cluster, users can modify the following:

    - The operating system
    - CUDA
    - OFED

A new node can be added using the following ways:

1. When the discovery mechanism is ``switch-based``:

    * Edit or append JSON list stored in ``switch-based-details`` in ``input/provision_config.yml``.

    .. note::
        * All ports residing on the same switch should be listed in the same JSON list element.
        * Ports configured via Omnia should be not be removed from ``switch-based-details`` in ``input/provision_config.yml``.


    * Run ``provision.yml``.

2. When the discovery mechanism is ``mapping``:

    * Update the existing mapping file by appending the new entry (without the disrupting the older entries) or provide a new mapping file by pointing ``pxe_mapping_file_path`` in ``provision_config.yml`` to the new location.

    * Run ``provision.yml``.

3. When the discovery mechanism is ``snmpwalk``:

    * Run ``provision.yml`` once the switch has discovered the potential new node.

4. When the discovery mechanism is ``bmc``:

    * Run ``provision.yml`` once the node has joined the cluster using an IP that exists within the provided range.


Alternatively, if a new mode is to be added with no change in configuration, run the following commands: ::

            cd provision
            ansible-playbook discovery_provision.yml





