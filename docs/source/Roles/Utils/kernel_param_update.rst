Update Kernel Parameters [1]_
========================

In Omnia, ``kernel_param_update`` is a utility designed to help users to add or modify kernel command-line parameters on the operating systems of the specified nodes. This tool allows users to change the behaviour of certain aspects of the OS kernel at boot time, enabling users to overwrite default values and set specific hardware settings according to their requirements.
For the supported kernel command-line parameters, `click here <https://docs.kernel.org/admin-guide/kernel-parameters.html>`_.

**Prerequisites**

* **Create an Inventory file**

    List all the nodes you wish to update the kernel parameters for, in a simple inventory file. For example: ::

        node3
        node1

* **Configure kernel parameters**

    Specify the kernel parameters you want to add or alter in the ``kernel_param_update_config.yml`` file. For example: ::

        GRUB_CMDLINE_LINUX="panic_print=1 print-fatal-signals=1"

.. note:: If you want to provide multiple kernel parameters, ensure that they are separated by a "space".

**To run the playbook**

Run the playbook using the following commands: ::

    ansible-playbook kernel_param_update.yml -i inventory

.. [1]

        This playbook has been validated with the following kernel parameters:

            * iommu=pt
            * intel_iommu=off
            * pci=realloc=off
            * processor.max_cstate=0
            * intel_idle.max_cstate=0
            * intel_pstate=disable
