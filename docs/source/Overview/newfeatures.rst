New Features
===========



*	`Extensive Telemetry and Monitoring <../Roles/Telemetry/index.html>`_ has been added to the Omnia stack, intended for consumption by customers that are using Dell systems and Omnia to provide SaaS/IaaS solutions.  These include, but are not limited to:

    –	CPU Utilization and status

    –	GPU utilization

    –	Node Count

    –	Network Packet I/O

    –	HDD capacity and free space

    –	Memory capacity and utilization

    –	Queued and Running Job Count

    –	User Count

    –	Cluster HW Health Checks (PCIE, NVLINK, BMC, Temps)

    –	Cluster SW Health Checks (dmesg, BeeGFS, k8s nodes/pods, mySQL on control plane)

*	Metrics are extracted using a combination of the following: PSUtil, Smartctl, beegfs-ctl, nvidia-smi, rocm-smi.  Since groundwork is already laid, additional requests from these tools will be quicker to implement in the future.

*	Telemetry and health checks can be optionally disabled.

*	`Log Aggregation <../Logging/ControlPlaneLogs.html>`_ via xCAT syslog:

    –	Aggregated on control plane, grouping default is “severity” with others available.

    –	Uses Grafani-Loki for viewing.

*	Automatic (empty) Docker Registry Creation.
