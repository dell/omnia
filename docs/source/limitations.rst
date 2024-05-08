Limitations
===========

-  Once ``provision.yml`` is used to configure devices, it is
   recommended to avoid rebooting the control plane.
- Omnia provision tools only support /16 subnet masks for provisioning.
-  Omnia supports adding only 1000 nodes when discovered via BMC.
-  Removal of Slurm and Kubernetes component roles are not supported.
   However, the scheduler type can be customized by setting ``scheduler_type`` in ``input/omnia_config.yml`` prior to running ``omnia.yml``.
-  After installing the Omnia control plane, changing the manager node
   is not supported. If you need to change the manager node, you must
   redeploy the entire cluster.
-  Dell Technologies provides support to the Dell-developed modules of
   Omnia. All the other third-party tools deployed by Omnia are outside
   the support scope.
-  To change the Kubernetes single node cluster to a multi-node cluster
   or change a multi-node cluster to a single node cluster, you must
   either redeploy the entire cluster or run ``kubeadm reset -f`` on all
   the nodes of the cluster. Then set ``scheduler_type:k8s`` in ``input/omnia_config.yml`` prior to running ``omnia.yml``.
-  In a single node cluster, the login node and Slurm functionalities
   are not applicable. However, Omnia installs FreeIPA Server and Slurm
   on the single node.
-  To change the Kubernetes version from 1.16 to 1.19 or 1.19 to 1.16,
   you must redeploy the entire cluster.
-  The Kubernetes pods will not be able to access the Internet or start
   when firewalld is enabled on the node. This is a limitation in
   Kubernetes. So, the firewalld daemon will be disabled on all the
   nodes as part of omnia.yml execution.
-  Only one storage instance (Powervault) is currently supported in the
   HPC cluster.
-  Omnia supports only basic telemetry configurations. Changing data
   fetching time intervals for telemetry is not supported.
-  Slurm cluster metrics will only be fetched from clusters configured
   by Omnia.
-  All iDRACs must have the same username and password.
-  OpenSUSE Leap 15.3 is not supported on the Control Plane.
-  Omnia might contain some unused MACs since LOM switch have both iDRAC MACs as well as ethernet MACs, PXE NIC ranges should contain IPs that are double the iDRACs present.
- FreeIPA authentication is not supported on the control plane.
- The multiple OS feature is only available with Rocky 8.7 when xCAT 2.16.5 is in use. Currently, Omnia uses 2.16.4.
- Currently, Omnia only supports the splitting of switch ports. Switch ports cannot be un-split using this script.
