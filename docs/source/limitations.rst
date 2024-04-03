Limitations
===========

-  Omnia supports adding only 1000 nodes when discovered via BMC.
-  Dell Technologies provides support to the Dell-developed modules of
   Omnia. All the other third-party tools deployed by Omnia are outside
   the support scope.
-  In a single node cluster, the login node and Slurm functionalities
   are not applicable. However, Omnia installs FreeIPA Server and Slurm
   on the single node.
-  Only one storage instance (Powervault) is currently supported in the
   HPC cluster.
-  Omnia supports only basic telemetry configurations. Altering the time intervals for telemetry data collection is not supported.
-  Slurm cluster metrics will only be fetched from clusters configured
   by Omnia.
-  All iDRACs must have the same username and password.
- Currently, Omnia only supports the splitting of switch ports. Switch ports cannot be un-split using the `switch configuration script <InstallationGuides/ConfiguringSwitches/index.html>`_.
- The IP subnet 10.4.0.0 cannot be used for any networks on the Omnia cluster as it is reserved for Nerdctl.