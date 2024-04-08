Creating node inventory
========================

When ``discovery_provision.yml``, ``prepare_cp.yml``, or ``utils/inventory_tagging.yml`` is run, a set of inventory files is created in ``/opt/omnia/omnia_inventory/`` based on `the Omnia database. <InstallingProvisionTool/ViewingDB.html>`_ The inventories are created based on the type of CPUs and GPUs nodes have. The inventory files are:

      * ``compute_cpu_amd`` ::

            [compute_cpu_amd]
            ABCD1



      * ``compute_cpu_intel`` ::

            [compute_cpu_intel]
            ABCD1

      * ``compute_gpu_amd`` ::

           [compute_cpu_amd]
           ABCD2
           ABCD3

      * ``compute_gpu_nvidia`` ::

            [compute_gpu_nvidia]
            ABCD1


      * ``compute_servicetag_ip`` ::

            [compute_servicetag_ip]
            ABCD1 ansible_host=10.5.0.2
            ABCD2 ansible_host=10.5.0.3
            ABCD3 ansible_host=10.5.0.4

  .. note::

      * Service tags will only be written into the inventory files after the nodes are successfully PXE booted post provisioning.
      * For a node's service tag to list in an inventory file, two conditions must be met:

                  * Node status must be "booted" in DB.
                  * Node's service tag information is present in DB.
      * To regenerate an inventory file, use the playbook ``utils/inventory_tagging.yml``.



