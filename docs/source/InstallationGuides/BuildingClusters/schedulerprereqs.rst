Before you build clusters
--------------------------

* Verify that all inventory files are updated.

* If the target cluster requires more than 10 kubernetes nodes, use a docker enterprise account to avoid docker pull limits.

* Verify that all nodes are assigned a group. Use the `inventory <../../samplefiles.html>`_ as a reference.

  * The manager group should have exactly 1 manager node.

  * The compute group should have at least 1 node.

  * The login group is optional. If present, it should have exactly 1 node.

  * Users should also ensure that all repos are available on the target nodes running RHEL.

.. note:: The inventory file accepts both IPs and FQDNs as long as they can be resolved by DNS.


* Nodes provisioned using the Omnia provision tool do not require a RedHat subscription to run ``scheduler.yml`` on RHEL target nodes.

* For RHEL target nodes not provisioned by Omnia, ensure that RedHat subscription is enabled on all target nodes. Every target node will require a RedHat subscription.

**Features enabled by omnia.yml**

* Slurm: Once all the required parameters in `omnia_config.yml <schedulerinputparams.html>`_ are filled in, ``omnia.yml`` can be used to set up slurm.

* Login Node (Additionally secure login node)

* Kubernetes: Once all the required parameters in `omnia_config.yml <schedulerinputparams.html>`_ are filled in, ``omnia.yml`` can be used to set up kubernetes.

* BeeGFS bolt on installation

* NFS bolt on support





  



