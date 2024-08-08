Performance profile configuration
==================================

.. caution:: Performance profile installation and accelerator configuration is supported exclusively for Intel Gaudi accelerators present in Ubuntu clusters.

Performance profiles enable you to optimize system performance for specific workloads. Omnia supports the configuration of performance profiles for Ubuntu clusters that have Intel Gaudi GPUs. These profiles come with predefined settings tailored to different use cases.
For more information, `click here <https://ubuntu.com/server/docs/tuned>`_.

**Prerequisites**

* **Create an Inventory file**

To configure performance profiles, list all the nodes for which you want to apply the profiles in an inventory file. A sample inventory looks like: ::

    node3
    node1

* **Configure Performance profiles**

In the ``utils/performance_config.yml`` file, under ``intel_gpu``, add or alter the values based on the following list of parameters:

.. csv-table:: Parameters for performance profile configuration
   :file: ../Tables/performance_config.csv
   :header-rows: 1
   :keepspace:

Here's a sample of the ``utils/performance_config.yml`` file:

.. image:: ../images/tuned_config.png

.. note:: For Intel Gaudi accelerators, Omnia recommends to add the ``vm.nr_hugepages`` as a ``profile_parameter`` under ``sysctl`` and set its value to 156300. Check out the sample image below:

    .. image:: ../images/tuneD_intel_habana.png
        :width: 300pt

* **Execute the the playbook**

Run the playbook using the following commands: ::

    ansible-playbook performance_setting.yml -i inventory