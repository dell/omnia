An Omnia cluster
==================

Omnia can deploy and configure PowerEdge servers, and build clusters that use Slurm or Kubernetes (or both) for workload management. Apart from the general compute servers (a.k.a. nodes) of a cluster, an Omnia cluster has two additional nodes:

1. **Control Plane**: The control plane is like a central node in a cluster, separate from the actual computing nodes. It acts as the main hub of the cluster, hosting the Omnia provisioning and monitoring tool. When setting up the cluster, the Omnia repository is copied and downloaded to the control plane.
2. **Head Node**: The head node in an Omnia cluster is a server that is responsible for hosting the scheduling manager (``kube_control_plane`` or ``slurm_control_node``). Similar to the control plane, the head node is separate from the compute nodes in the cluster. It plays a crucial role in managing the scheduling of tasks within the cluster.

Omnia "AI" cluster
-------------------

Components of an AI-driven Omnia cluster are:

1. Compute nodes
2. Control plane
3. Head node - From an AI perspective, the head node is nothing but the ``kube_control_plane`` used to manage Kubernetes jobs on the cluster.

Omnia "HPC" cluster
--------------------

Components of an HPC Omnia cluster are:

1. Compute nodes
2. Control plane
3. Head node - From an HPC perspective, the head node is nothing but the ``slurm_control_node`` used to manage slurm jobs on the cluster.
4. [Optional] Login node