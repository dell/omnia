# Pre-Requisites Before Running `telemetry.yml`

## Prerequisites to Enabling iDRAC Telemetry
* All target devices should run iDRAC firmware version > 4.
* All target devices should have a datacenter license.

## Prerequisites to Enabling Slurm Telemetry
* Slurm Telemetry cannot be executed without iDRAC support
* Omnia control plane should be executed and node_inventory should be created in awx.
* The slurm manager and compute nodes are fetched at run time from node_inventory.
* Slurm should be installed on the nodes, if not there is no point in executing slurm telemetry.
* A minimum of one cluster is required for Slurm Telemetry to work.
* Once telemetry is running, delete the pods and images on control plane if a cluster change is intended.

Once all pre-requisites are met, enter the required input parameters based on the [provided guides](../Input_Parameter_Guide/Telemetry_Visualization_Parameters).