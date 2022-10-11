**Telemetry Parameters**

``telemetry_base_vars.yml``

+-------------------------+-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Parameter Name          | Default Value                     | Information                                                                                                                                                                                               |
+=========================+===================================+===========================================================================================================================================================================================================+
| idrac_telemetry_support | true                              | This   variable is used to enable iDRAC telemetry support and visualizations.   Accepted Values: true/false                                                                                               |
+-------------------------+-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| slurm_telemetry_support | true                              | This variable is used to enable slurm   telemetry support and visualizations. Slurm Telemetry support can only be   activated when idrac_telemetry_support is set to true. Accepted Values:   True/False. |
+-------------------------+-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| timescaledb_name        | telemetry_metrics                 | Postgres   DB with timescale extension is used for storing iDRAC and slurm telemetry   metrics.                                                                                                           |
+-------------------------+-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| mysqldb_name            | idrac_telemetrysource_services_db | MySQL DB is used to store IPs and   credentials of iDRACs having datacenter license                                                                                                                       |
+-------------------------+-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+


``telemetry_login_vars.yml``

+-----------------------+---------------+-----------------------------------------------------------+
| Parameter Name        | Default Value | Information                                               |
+=======================+===============+===========================================================+
| timescaledb_user      |               | Username   used for connecting to timescale db.           |
|                       |               |                                                           |
|                       |               | Minimum Length: 2 characters.                             |
|                       |               |                                                           |
|                       |               | The username must not contain -,, ',"                     |
+-----------------------+---------------+-----------------------------------------------------------+
| timescaledb_password  |               | Password used for connecting to   timescale db.           |
|                       |               |                                                           |
|                       |               | Minimum Length: 2 characters.                             |
|                       |               |                                                           |
|                       |               | The password must not contain -,, ',",@                   |
+-----------------------+---------------+-----------------------------------------------------------+
| mysqldb_user          |               | Username   used for connecting to mysql db.               |
|                       |               |                                                           |
|                       |               | Minimum Length: 2 characters.                             |
|                       |               |                                                           |
|                       |               | The username must not contain -,, ',"                     |
+-----------------------+---------------+-----------------------------------------------------------+
| mysqldb_password      |               | Password used for connecting to mysql   db.               |
|                       |               |                                                           |
|                       |               | Minimum Length: 2 characters.                             |
|                       |               |                                                           |
|                       |               | The password must not contain -,, ',"                     |
+-----------------------+---------------+-----------------------------------------------------------+
| mysqldb_root_password |               | Password   used for connecting to mysql db for root user. |
|                       |               |                                                           |
|                       |               | Minimum Legth: 2 characters.                              |
|                       |               |                                                           |
|                       |               | The password must not contain -,, ',"                     |
+-----------------------+---------------+-----------------------------------------------------------+