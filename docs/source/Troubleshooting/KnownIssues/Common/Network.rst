Network
========

⦾ **During consecutive runs of the** ``server_spec_update.yml`` **playbook, the additional NICs may not be configured according to the inputs provided in the** ``input/server_spec.yml`` **file, or any unexpected behavior may occur.**

**Potential Cause**: Omnia does not support modifying the category definitions (for example, ``nic_name``, ``nicnetwork``, or ``nictype``) in ``input/server_spec.yml`` or changing the category details in the inventory file provided, during consecutive runs of the ``server_spec_update.yml`` playbook.

**Resolution**: Re-provision the nodes.
