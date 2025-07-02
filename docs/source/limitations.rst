Limitations
===========

- Omnia supports adding only 1000 nodes when discovered via BMC.
- Dell Technologies provides support to the Dell-developed modules of Omnia. All the other third-party tools deployed by Omnia are outside the support scope.
- In a single node cluster, the login node and Slurm functionalities are not applicable.
- Containerized benchmark job execution is not supported on Slurm clusters.
- Only one storage instance (PowerVault) is currently supported in the HPC cluster.
- All iDRACs must have the same username and password.
- The IP subnet 10.4.0.0 cannot be used for any networks on the Omnia cluster as it is reserved for Nerdctl.
- Omnia playbooks will fail if the OIM is unable to reach the online resource or Internet.