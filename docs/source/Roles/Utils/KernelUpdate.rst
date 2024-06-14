Updating kernels
=================

**Pre requisites**:

* All target nodes should be running RHEL, Rocky Linux, or Ubuntu OS.
* Download the kernel packages using ``local_repo.yml``. For more information, `click here <../../InstallationGuides/LocalRepo/index.html>`_.
* Verify that the cluster nodes are in the ``booted`` state. For more information, `click here <../InstallationGuides/InstallingProvisionTool/ViewingDB.html>`_.


**Install kernel updates to cluster nodes**

1. Go to ``utils/software_update`` and edit ``software_update_config.yml``, as per the parameters table below.

.. csv-table:: Parameters for Kernel Update
      :file: ../../Tables/kernel_update.csv
      :header-rows: 1
      :keepspace:

2. To run the playbook, run the following commands: ::

       cd utils/software_update
       ansible-playbook software_update.yml -i inventory

.. note:: Inventory should contain the IP/hostname/service tag of the target nodes. For example,
    ::
        10.5.0.101
        10.5.0.102

3. After execution is completed, verify that kernel packages are on the nodes using:
            * For RHEL/Rocky Linux: ``rpm -qa | grep kernel``
            * For Ubuntu: ``dpkg -l | grep linux-generic``