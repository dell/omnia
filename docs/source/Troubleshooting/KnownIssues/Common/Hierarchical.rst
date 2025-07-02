Hierarchical cluster
=====================

⦾ **If the admin NIC on the OIM is named** ``nic1`` **, but the service node already has a different NIC with the same name (even if it's not used as the admin NIC), the post-boot script on the active service node fails to rename the intended admin NIC.**

**Potential Cause**: A conflicting NIC with the same name (``nic1``, for example) exists on the service node. This issue occurs during the ``discovery_provision.yml`` playbook execution. Although the playbook passes and the nodes boot successfully (with their status updated in the OmniaDB), any subsequent attempts to provision the compute nodes fails.

**Resolution**: Ensure the admin NIC name on the service node matches the OIM’s admin NIC name, and no other NIC (even inactive) has the same name.