Creating node inventory
------------------------

When ``provision.yml``, ``prepare_cp.yml``, or ``utils/inventory_tagging.yml`` is run, a set of inventory files is created in `/opt/omnia/omnia_inventory/``. The inventories are created based on the type of CPUs and GPUs nodes have. The inventory files are:
                                                                                                                                                                                                           * ``compute_cpu_amd``
      * ``compute_cpu_intel``
      * ``compute_gpu_amd``
      * ``compute_gpu_nvidia``
      * ``compute_servicetag_ip``

  .. note::

      * Service tags will only be written into the inventory files after the nodes are successfully PXE booted post provisioning.
      * Nodes must be booted and the service tag must be in the DB for nodes to list in the Inventory file.
      * To regenerate an inventory file, use the playbook ``utils/inventory_tagging.yml``.



