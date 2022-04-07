# Parameters in `telemetry_login_vars.yml`
Before running `telemetry.yml`, ensure that the files in `/telemetry/input_params/` are filled in.


| Parameter Name        | Default Value | Information |
|-----------------------|---------------|-------------|
| timescaledb_user      | 		        |  Username used for connecting to timescale db. Minimum Length: 2 characters. <br> The username must not contain -,\, ',"         |
| timescaledb_password  | 		        |  Password used for connecting to timescale db. Minimum Length: 2 characters. <br> The password must not contain -,\, ',",@          |
| mysqldb_user          | 		        |  Username used for connecting to mysql db. Minimum Length: 2 characters. <br>  The username must not contain -,\, ',"       |
| mysqldb_password      | 		        |  Password used for connecting to mysql db. Minimum Length: 2 characters. <br> The password must not contain -,\, ',"          |
| mysqldb_root_password | 		        |  Password used for connecting to mysql db for root user. Minimum Legth: 2 characters. <br> The password must not contain -,\, ',"        |