Provision
==========

⦾ **While provisioning a node in an Ubuntu cluster, "Installing" status is not displayed in cluster.nodeinfo table.**

**Resolution**: User can track provisioning progress by checking the supported status types. If the status shows ``bmcready`` or ``powering-on``, user can infer that the node is being provisioned. Once the node has been provisioned successfully, it will reflect a ``booted`` status in the OmniaDB.