Software Update
++++++++++++++++++

To install multiple packages on target nodes in a bulk operation, the ``software_update.yml`` playbook can be leveraged.

**Prerequisites**

    * All target nodes should be running RHEL, Rocky, or Ubuntu OS.
    * Download the packages using ``local_repo.yml``. For more information, `click here <../../LocalRepo/index.html>`_.


To customize the software update, enter the following parameters in ``utils/software_update/software_update_config.yml``:

.. csv-table:: Parameters for software_update_config.yml
      :file: ../../Tables/software_update_config.csv
      :header-rows: 1
      :keepspace:

To run the playbook, run the following commands: ::

    cd utils/software_update
    ansible-playbook software_update.yml -i inventory

Inventory should contain the IP of the target nodes. For example, ::

    10.5.0.101
    10.5.0.102