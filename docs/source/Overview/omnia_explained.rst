Types of clusters deployed by Omnia
======================================

Omnia can deploy and configure PowerEdge servers (nodes), and build clusters that use Slurm or Kubernetes (or both) for workload management. Apart from the general compute nodes of the cluster, a cluster deployed by Omnia has two additional nodes:

1. **Omnia Infrastructure Manager (OIM)**: The OIM is like a central node in a cluster, separate from the actual computing nodes. It acts as the main hub of the cluster, hosting the Omnia provisioning and monitoring tool. When setting up the cluster, the Omnia repository is copied and downloaded to the OIM.
2. **Head Node**: The head node in an Omnia cluster is a server that is responsible for hosting the scheduling manager (``kube_control_plane`` or ``slurm_control_node``). Similar to the OIM, the head node is separate from the compute nodes in the cluster. It plays a crucial role in managing the scheduling of tasks within the cluster.

Kubernetes cluster
-------------------

Components of a Kubernetes cluster are:

* **Head node**: In a Kubernetes cluster deployed by Omnia, the head node is nothing but the ``kube_control_plane`` used to manage Kubernetes jobs on the cluster.
* **Compute nodes**: In a Kubernetes cluster, the ``kube_node``(s) function as the compute nodes.
* **etcd node**: Etcd is an open-source distributed key-value store that is used to store and manage the information that distributed systems need for their operations. It stores the configuration data, state data, and metadata in Kubernetes.

Slurm cluster
----------------

Components of a Slurm cluster are:

* **Head node**: In an HPC cluster, the head node is nothing but the ``slurm_control_node`` used to manage slurm jobs on the cluster.
* **Compute nodes**: In an HPC cluster, a compute node is nothing but a ``slurm_node``.
* **[Optional] Login node**: In Omnia, a login node serves as an extra layer of authentication. Users are required to authenticate themselves through this additional login node, which is configured by Omnia. This setup allows the cluster administrator to limit direct access to the head node (also referred to as ``slurm_control_node``) by users. The login node acts as a gateway for users to securely access the cluster.

.. note:: If a login node is not present in a Slurm cluster, then only users with access to the head node can submit Slurm jobs.