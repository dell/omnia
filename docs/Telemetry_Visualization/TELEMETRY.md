# Setting Up Grafana

Using Grafana, users can poll multiple devices and create graphs/visualizations of key system metrics such as temperature, System power consumption, Memory Usage, IO Usage, CPU Usage, Total Memory Power, System Output Power, Total Fan Power, Total Storage Power, System Input Power, Total CPU Power, RPM Readings, Total Heat Dissipation, Power to Cool ratio, System Air Flow Efficiency etc.

A lot of these metrics are collected using iDRAC telemetry. iDRAC telemetry allows you to stream telemetry data from your servers to a centralized log/metrics server. For more information on iDRAC telemetry, click [here]( https://github.com/dell/iDRAC-Telemetry-Reference-Tools).

## Prerequisites

1. To set up Grafana, ensure that `control_plane/input_params/login_vars.yml` is updated with the Grafana Username and Password.
2. All [parameters](../Input_Parameter_Guide/Telemetry_Visualization_Parameters/telemetry_login_vars.md) in `telemetry/input_params/telemetry_login_vars.yml` need to be filled in.
3. All [parameters](../Input_Parameter_Guide/Telemetry_Visualization_Parameters/telemetry_base_vars.md) in `telemetry/input_params/telemetry_base_vars.yml` need to be filled in.
4. Find the IP of the Grafana UI using:
 
`kubectl get svc -n grafana`

## Logging into Grafana

Use any one of the following browsers to access the Grafana UI (https://< Grafana UI IP >:5000):
* Chrome/Chromium
* Firefox
* Safari
* Microsoft Edge

>> **Note**: Always enable JavaScript in your browser. Running Grafana without JavaScript enabled in the browser is not supported.

## Prerequisites to Enabling Slurm Telemetry

* Slurm Telemetry cannot be executed without iDRAC support
* Omnia control plane should be executed and node_inventory should be created in awx.
* The slurm manager and compute nodes are fetched at run time from node_inventory.
* Slurm should be installed on the nodes, if not there is no point in executing slurm telemetry.
* A minimum of one cluster is required for Slurm Telemetry to work.
* Once telemetry is running, delete the pods and images on control plane if a cluster change is intended.

## Initiating Telemetry

1. Once `control_plane.yml` and `omnia.yml` are executed, run the following commands from `omnia/telemetry`:

`ansible-playbook telemetry.yml`

>> **Note**: Telemetry Collection is only initiated on iDRACs on AWX that have a datacenter license and are running a firmware version of 4 or higher.

## Adding a New Node to Telemetry
After initiation, new nodes can be added to telemetry by running the following commands from `omnia/telemetry`:
		
`ansible-playbook add_idrac_node.yml`