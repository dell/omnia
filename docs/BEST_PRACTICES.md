# Best Practices When Using Omnia
* Ensure that PowerCap policy is disabled and the BIOS system profile is set to 'Performance' on the Control Plane.
* Ensure that there is at least 50% (~35%)free space on the Control Plane before running Omnia.
* Disable SElinux on the Control Plane.
* Use a [host mapping file](../examples/host_mapping_file_os_provisioning.csv) and [device mapping file](../examples/mapping_device_file.csv) even when using DHCP configuration to ensure that IP assignments remain persistent across Control Plane reboots.
* Avoid rebooting the Control Plane as much as possible to ensure that all network configuration does not get disturbed.
* Review the [PreRequisites](PreRequisites) before running Omnia Scripts.
* If telemetry is to be enabled using Omnia, use AWX to deploy Slurm/Kubernetes.