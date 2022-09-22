# Limitations
* Once `control_plane.yml` is used to configure devices, it is recommended to avoid rebooting the control plane.
* If the control plane reboots, DHCP services restart. Devices that have had their IP assigned dynamically via DHCP may get assigned new IPs. This in turn can cause duplicate entries for the same device on AWX. Clusters may also show inconsistency and ambiguity.
* Removal of Slurm and Kubernetes component roles are not supported. However, skip tags can be provided at the start of installation to select the component roles.
* After installing the Omnia control plane, changing the manager node is not supported. If you need to change the manager node, you must redeploy the entire cluster.
* Dell Technologies provides support to the Dell-developed modules of Omnia. All the other third-party tools deployed by Omnia are outside the support scope.
* To change the Kubernetes single node cluster to a multi-node cluster or change a multi-node cluster to a single node cluster, you must either redeploy the entire cluster or run `kubeadm reset -f` on all the nodes of the cluster. You then need to run the `omnia.yml` file and skip the installation of Slurm using the skip tags.
* In a single node cluster, the login node and Slurm functionalities are not applicable. However, Omnia installs FreeIPA Server and Slurm on the single node.
* To change the Kubernetes version from 1.16 to 1.19 or 1.19 to 1.16, you must redeploy the entire cluster.
* The Kubernetes pods will not be able to access the Internet or start when firewalld is enabled on the node. This is a limitation in Kubernetes. So, the firewalld daemon will be disabled on all the nodes as part of omnia.yml execution.
* Only one storage instance (Powervault) is currently supported in the HPC cluster.
* Cobbler web support has been discontinued from Omnia 1.2 onwards.
* Omnia supports only basic telemetry configurations. Changing data fetching time intervals for telemetry is not supported.
* Slurm cluster metrics will only be fetched from clusters configured by Omnia.
* All iDRACs must have the same username and password.
* OpenSUSE Leap 15.3 is not supported on the Control Plane.
* Slurm Telemetry is supported only on a single cluster.
* When `roce_network_nic` is provided when running `control_plane.yml`,  `host_mapping_file_path` is disregarded. This means that static IP assignment is not supported when using high speed data paths for provisioning.
* AWX auto aborts jobs when there are more than 5 nodes in a cluster. To manage larger clusters, please use Ansible CLI.
