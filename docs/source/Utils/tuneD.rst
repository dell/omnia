TuneD accelerator configuration
================================

.. caution:: TuneD profile installation and accelerator configuration is supported exclusively for Intel Gaudi accelerators present in Ubuntu clusters.

TuneD profiles enable you to optimize system performance for specific workloads. Omnia supports the configuration of TuneD profiles for Ubuntu clusters that have Intel Gaudi GPUs. These profiles come with predefined settings tailored to different use cases.
For more information related to TuneD, `click here <https://ubuntu.com/server/docs/tuned>`_.

**Prerequisites**

* **Create an Inventory file**

To configure TuneD profiles, list all the nodes for which you want to apply the profiles in an inventory file. For example: ::

    node3
    node1

* **Configure TuneD profiles**

In the ``utils/performance_profile_config.yml`` file, under ``intel_gpu``, add or alter the values based on the following list of parameters:

.. csv-table:: Parameters for TuneD configuration
   :file: ../Tables/tuned_config.csv
   :header-rows: 1
   :keepspace:

Here's a sample of the ``utils/performance_profile_config.yml`` file:

.. image:: ../images/tuned_config.png

.. note:: For Intel Gaudi accelerators, Omnia recommends to add the ``vm.nr_hugepages`` parameter and set its value to 156300. Check out the sample image below:

    .. image:: ../images/tuneD_intel_habana.png
        :width: 400pt

* **Execute the the playbook**

Run the playbook using the following commands: ::

    ansible-playbook performance_profile.yml -i inventory