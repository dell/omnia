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

In the ``utils/performance_profile/performance_profile_config.yml`` file, under ``intel_gpu``, add or alter the values based on the following list of parameters:

.. csv-table:: Parameters for performance profile configuration
   :file: ../Tables/performance_config.csv
   :header-rows: 1
   :keepspace:

Here's a sample of the default ``performance_profile_config.yml`` file: ::

    intel_gpu:
      performance_profile: "accelerator-performance"
      performance_profile_plugin:
        sysctl:
          - vm.nr_hugepages: 156300
      reboot_required: "no"

Here's an example for adding/modifying multiple plugins in the ``performance_profile_config.yml`` file: ::

      intel_gpu:
      performance_profile: "accelerator-performance"
      performance_profile_plugin:
        sysctl:
          - vm.nr_hugepages: 156300
        cpu:
          - force_latency: 99
        disk:
          - read_ahead_kb: 4096
        reboot_required: "no"

.. note:: For Intel Gaudi accelerators, Omnia recommends to add the ``vm.nr_hugepages`` as a profile parameter under ``sysctl`` plugin and set its value to 156300.

* **Execute the the playbook**

Run the playbook using the following commands: ::

    ansible-playbook performance_profile.yml -i inventory