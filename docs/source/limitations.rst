Limitations
===========

- Omnia supports adding only 1000 nodes when discovered via BMC.
- Dell Technologies provides support to the Dell-developed modules of
  Omnia. All the other third-party tools deployed by Omnia are outside
  the support scope.
- In a single node cluster, the login node and Slurm functionalities
  are not applicable. However, Omnia installs FreeIPA Server and Slurm
  on the single node.
- Omnia does not currently support Slurm on Ubuntu.
- Containerized benchmark job execution is not supported on Slurm clusters.
- FreeIPA server is not provided in the default Ubuntu repositories. OpenLDAP is provided as an alternative.
- Only one storage instance (Powervault) is currently supported in the
  HPC cluster.
- Omnia supports only basic telemetry configurations. Altering the time intervals for telemetry data collection is not supported.
- Slurm cluster metrics will only be fetched from clusters configured
  by Omnia.
- All iDRACs must have the same username and password.
- Currently, Omnia only supports the splitting of switch ports. Switch ports cannot be un-split using the `switch configuration script <InstallationGuides/ConfiguringSwitches/index.html>`_.
- The IP subnet 10.4.0.0 cannot be used for any networks on the Omnia cluster as it is reserved for Nerdctl.
- Installation of vLLM and racadam via Omnia is not supported on Ubuntu 20.04.
- Omnia v1.6 does not support configuration of a DNS server on the control plane; that is, the ``DNS`` parameter in `input/network_spec.yml <InstallationGuides/InstallingProvisionTool/provisionparams.html>`_ is not supported.
- The "desktop image" version of Ubuntu is not supported on the control plane.
- Omnia does not allow users to perform downgrade operations, which means that once they have upgraded their setup, they cannot revert back to a previous version of Omnia.
