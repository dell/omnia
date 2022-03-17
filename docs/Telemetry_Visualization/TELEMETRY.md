# Setting Up Grafana

Using Grafana, users can poll multiple devices and create graphs/visualizations of key system metrics such as temperature, System power consumption, Memory Usage, IO Usage, CPU Usage, Total Memory Power, System Output Power, Total Fan Power, Total Storage Power, System Input Power, Total CPU Power, RPM Readings, Total Heat Dissipation, Power to Cool ratio, System Air Flow Efficiency etc.

A lot of these metrics are collected using iDRAC telemetry. iDRAC telemetry allows you to stream telemetry data from your servers to a centralized log/metrics servers. For more information on iDRAC telemetry, click [here]( https://github.com/dell/iDRAC-Telemetry-Reference-Tools).

## Prerequisites

1. To set up Grafana, ensure that `control_plane/input_params/login_vars.yml` is updated with the Grafana Username and Password.
2. All parameters in `telemetry/input_params/telemetry_login_vars.yml` need to be filled in:

| Parameter Name        | Default Value | Information |
|-----------------------|---------------|-------------|
| timescaledb_user      | 		        |  Username used for connecting to timescale db. Minimum Length: 2 characters.          |
| timescaledb_password  | 		        |  Password used for connecting to timescale db. Minimum Length: 2 characters.           |
| mysqldb_user          | 		        |  Username used for connecting to mysql db. Minimum Length: 2 characters.         |
| mysqldb_password      | 		        |  Password used for connecting to mysql db. Minimum Length: 2 characters.            |
| mysqldb_root_password | 		        |  Password used for connecting to mysql db for root user. Minimum Legth: 2 characters.         |

3. All parameters in `telemetry/input_params/telemetry_base_vars.yml` need to be filled in:

| Parameter Name          | Default Value     | Information |
|-------------------------|-------------------|-------------|
| mount_location          | /opt/omnia 		  | Sets the location all telemetry related files will be stored and both timescale and mysql databases will be mounted.            |
| idrac_telemetry_support | true              | This variable is used to enable iDRAC telemetry support and visualizations. Accepted Values: true/false            |
| slurm_telemetry_support | true              | This variable is used to enable slurm telemetry support and visualizations. Slurm Telemetry support can only be activated when idrac_telemetry_support is set to true. Accepted Values: True/False.        |
| timescaledb_name        | telemetry_metrics | Postgres DB with timescale extension is used for storing iDRAC and slurm telemetry metrics.            |
| mysqldb_name			  | idrac_telemetrysource_services_db | MySQL DB is used to store IPs and credentials of iDRACs having datacenter license           |

3. Find the IP of the Grafana UI using:
 
`kubectl get svc -n grafana`

## Logging into Grafana

Use any one of the following browsers to access the Grafana UI (https://< Grafana UI IP >:5000):
* Chrome/Chromium
* Firefox
* Safari
* Microsoft Edge

>> __Note:__ Always enable JavaScript in your browser. Running Grafana without JavaScript enabled in the browser is not supported.

## Prerequisites to Enabling Slurm Telemetry

* Slurm Telemetry cannot be executed without iDRAC support
* Omnia control plane should be executed and node_inventory should be created in awx.
* The slurm manager and compute nodes are fetched at run time from node_inventory.
* Slurm should be installed on the nodes, if not there is no point in executing slurm telemetry.

## Initiating Telemetry

1. Once `control_plane.yml` and `omnia.yml` are executed, run the following commands from `omnia/telemetry`:

`ansible-playbook telemetry.yml`

>> __Note:__ Telemetry Collection is only initiated on iDRACs on AWX that have a datacenter license and are running a firmware version of 4 or higher.

## Adding a New Node to Telemetry
After initiation, new nodes can be added to telemetry by running the following commands from `omnia/telemetry`:
		
` ansible-playbook add_idrac_node.yml `

	
