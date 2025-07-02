High Availability (HA)
======================

⦾ **In a HA-setup, the xCAT post-installation script fails while switching from an active to passive OIM, during failover scenarios. This halts the ongoing OS-provisioning on the compute nodes.**

**Potential Cause**: This issue occurs due to an open defect in xCAT. For more information, `click here <https://github.com/xcat2/xcat-core/issues/7503>`_.

**Resolution**: If this occurs, wait until all containers have fully transitioned and confirm that the ``omnia_pcs`` container is up and running on the passive OIM node. Then, re-run any failed OS provisioning tasks.

⦾ **In an HA-enabled OIM setup, when the active OIM fails due to any hardware issues, all the containers and resources are moved to the passive OIM. However, if the admin NIC on the passive node subsequently malfunctions, the containers try to fail back over to the original (previously active) OIM node. This results in failure, with logs showing the error:** ``Resource temporarily unavailable``. **Additionally, both OIM nodes show each other as offline in** ``pcs_status``.

**Potential Cause**: The issue occurs because the passive node, although its NIC is disabled, continues to run containers. The HA stack is unable to synchronize the state between the two OIM nodes, leading to a split-brain scenario where both nodes operate independently and fail to coordinate resource management. As a result, containers attempt to start on both nodes simultaneously, causing service conflicts and instability.

**Resolution**: Ensure that the failed NIC on the affected OIM node is fixed, and the node is properly shut down before HA failover is triggered. This allows the healthy OIM node to take over completely and operate without container conflicts. After resolving the hardware issue, power on the repaired OIM node to restore full HA functionality and sync between nodes.