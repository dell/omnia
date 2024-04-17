Updating kernels
=================

**Pre requisites**:

* All target nodes should be running RHEL, Rocky, or Ubuntu OS.
* Download the kernel packages using ``local_repo.yml``. For more information, `click here <../../LocalRepo/index.html>`_.
* Verify that the cluster nodes are in the ``booted`` state. For more information, `click here <../InstallingProvisionTool/ViewingDB.html>`_.

**Install kernel updates to cluster nodes**

1. Go to ``utils/software_update`` and edit ``software_update_config.yml``. For more information on the input parameters, `click here <software_update.html>`_.
2. Run ``software_update.yml`` using : ``ansible-playbook software_update.yml -i inventory``
3. After execution is completed, verify that kernel packages are on the nodes using:
            * For RHEL/Rocky: ``rpm -qa | grep kernel``
            * For Ubuntu: ``dpkg -l | grep linux-generic``