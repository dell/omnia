An Omnia cluster
==================

Omnia can deploy and configure PowerEdge servers (a.k.a. nodes), and build clusters that use Slurm or Kubernetes (or both) for workload management. Apart from the general compute nodes of a cluster, an Omnia cluster has two additional nodes:

1. **Control Plane**: The control plane is like a central node in a cluster, separate from the actual computing nodes. It acts as the main hub of the cluster, hosting the Omnia provisioning and monitoring tool. When setting up the cluster, the Omnia repository is copied and downloaded to the control plane.
2. **Head Node**: The head node in an Omnia cluster is a server that is responsible for hosting the scheduling manager (``kube_control_plane`` or ``slurm_control_node``). Similar to the control plane, the head node is separate from the compute nodes in the cluster. It plays a crucial role in managing the scheduling of tasks within the cluster.

Omnia "AI" cluster
-------------------

Components of an AI-driven Omnia cluster are:

* **Head node**: In an AI workload-driven Omnia cluster, the head node is nothing but the ``kube_control_plane`` used to manage Kubernetes jobs on the cluster.
* **Compute nodes**: In an AI cluster, a compute node is nothing but a ``kube_node``.

Omnia "HPC" cluster
--------------------

Components of an HPC Omnia cluster are:

* **Head node**: In an HPC cluster, the head node is nothing but the ``slurm_control_node`` used to manage slurm jobs on the cluster.
* **Compute nodes**: In an HPC cluster, a compute node is nothing but a ``slurm_node``.
* **[Optional] Login node**: In Omnia, a login node serves as an extra layer of authentication. Users are required to authenticate themselves through this additional login node, which is configured by Omnia. This setup allows the cluster administrator to limit direct access to the head node (also referred to as ``slurm_control_node``) by users. The login node acts as a gateway for users to securely access the cluster.