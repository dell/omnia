Updating kernels
=================

**Pre requisites**:

* All target nodes should be running RHEL, Rocky, or Ubuntu OS.
* Download the kernel packages using ``local_repo.yml``. For more information, `click here <../../LocalRepo/index.html>`_.
* Verify that the cluster nodes are in the ``booted`` state. For more information, `click here <../InstallingProvisionTool/ViewingDB.html>`_.

.. csv-table:: Parameters for Kernel Update
      :file: ../../Tables/kernel_update.csv
      :header-rows: 1
      :keepspace:

**Install kernel updates to cluster nodes**

1. Go to ``utils/software_update`` and edit ``software_update_config.yml``.
2. To run the playbook, run the following commands: ::

       cd utils/software_update
       ansible-playbook software_update.yml -i inventory

    Inventory should contain the IP/hostname/service tag of the target nodes. For example, ::

           10.5.0.101
           10.5.0.102

3. After execution is completed, verify that kernel packages are on the nodes using:
            * For RHEL/Rocky: ``rpm -qa | grep kernel``
            * For Ubuntu: ``dpkg -l | grep linux-generic``