# Parameters in `telemetry_base_vars.yml`

Before running `telemetry.yml`, ensure that the files in `/telemetry/input_params/` are filled in.


| Parameter Name          | Default Value     | Information |
|-------------------------|-------------------|-------------|
| idrac_telemetry_support | true              | This variable is used to enable iDRAC telemetry support and visualizations. Accepted Values: true/false            |
| slurm_telemetry_support | true              | This variable is used to enable slurm telemetry support and visualizations. Slurm Telemetry support can only be activated when idrac_telemetry_support is set to true. Accepted Values: True/False.        |
| timescaledb_name        | telemetry_metrics | Postgres DB with timescale extension is used for storing iDRAC and slurm telemetry metrics.            |
| mysqldb_name			  | idrac_telemetrysource_services_db | MySQL DB is used to store IPs and credentials of iDRACs having datacenter license           |