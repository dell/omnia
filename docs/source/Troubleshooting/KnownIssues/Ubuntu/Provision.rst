Provision
==========

⦾ **While provisioning a node in an Ubuntu cluster,** ``Installing`` **status is not displayed in cluster.nodeinfo table.**

**Potential Cause**: This failure is caused due to an issue with xCAT, a third-party software. For more information about this issue, `click here <https://github.com/xcat2/xcat-core/issues/7488>`_.

**Resolution**: User can track provisioning progress by checking the supported status types. If the status shows ``bmcready`` or ``powering-on``, user can infer that the node is being provisioned. Once the node has been provisioned successfully, it will reflect a ``booted`` status in the OmniaDB.