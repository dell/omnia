Before you build clusters
--------------------------

* `Ensure that all cluster nodes are up and running <../Provision/ViewingDB.html>`_.

* Verify that the inventory file is updated as mentioned in the `inventory sample file <../../samplefiles.html>`_.

     * For Slurm, all the applicable inventory groups are ``slurm_control_node``, ``slurm_node``, and ``login``.
     * For Kubernetes, all the applicable groups are ``kube_control_plane``, ``kube_node``, and ``etcd``.
     * The centralized authentication server inventory group, that is ``auth_server``, is common for both Slurm and Kubernetes.
     * For secure login node functionality, ensure to add the ``login`` group in the provided inventory file.

* Verify that all nodes are assigned a group. The inventory file is case-sensitive. Follow the format provided in the `sample file link <../../samplefiles.html>`_.

.. note::
    * The inventory file accepts both IPs and FQDNs as long as they can be resolved by DNS.
    * In a multi-node setup, an IP cannot be listed as a control node and a compute node simultaneously. That is, don't include the ``kube_control_plane`` IP address in the compute node group. In a single node setup, the compute node and the ``kube_control_plane`` must be the same.

* Users should also ensure that all repositories are available on the cluster nodes.

* If the cluster requires more than 10 kubernetes nodes, use a docker enterprise account to avoid docker pull limits.





  



