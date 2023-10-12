Before you build clusters
--------------------------

* `Ensure that all cluster nodes are up and running <../InstallingProvisionTool/ViewingDB.html>`_.

* Verify that all inventory files are updated.

* If the cluster requires more than 10 kubernetes nodes, use a docker enterprise account to avoid docker pull limits.

* Verify that all nodes are assigned a group. Use the `inventory <../../samplefiles.html>`_ as a reference. The inventory file is case-sensitive. Follow the casing provided in the sample file link.

  * The manager group should have exactly 1 manager node.

  * The compute group should have at least 1 node.

  * The login group is optional. If present, it should have exactly 1 node.

.. note::
    * The inventory file accepts both IPs and FQDNs as long as they can be resolved by DNS.
    * In a multi-node setup, IP's cannot be repeated in the manager or compute groups. That is, don't include the manager node IP address in the compute group. In a single node setup, the compute node and the manager node must be the same.

* Users should also ensure that all repos are available on the cluster nodes running RHEL.

* Nodes provisioned using the Omnia provision tool do not require a RedHat subscription to run ``omnia.yml`` on RHEL cluster nodes.

* For RHEL cluster nodes not provisioned by Omnia, ensure that RedHat subscription is enabled on all target nodes. Every target node will require a RedHat subscription.




  



