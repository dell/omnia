Add New Nodes
==============

If a new node is provisioned through Cobbler, the node address is automatically displayed on the AWX dashboard. The node is not assigned to any group. You can add the node to the compute group along with the existing nodes and run ``omnia.yml`` to add the new node to the cluster and update the configurations in the manager node.
