TimescaleDB utility
-------------------

Telemetry metrics stored in a timescaleDB can be copied locally in a csv format. This file can be used to generate insights into key statistics in your cluster.

To customize the local copy of the timescale DB, fill out the below parameters in ``utils/timescaledb_utility/timescaledb_utility_config.yml``.

+------------------+---------------------------------------------------------------------------------------------------------+
| Parameter        | Details                                                                                                 |
+==================+=========================================================================================================+
| **column_name**  | * Filters timescaleDB data by metric name **and** value.                                                |
| ``string``       | * If this value is not provided, all metrics and their corresponding values will be stored in the file. |
| Optional         |                                                                                                         |
+------------------+---------------------------------------------------------------------------------------------------------+
| **column_value** | * Filters timescaleDB data by metric name **and** value.                                                |
| ``string``       | * If this value is not provided, all metrics and their corresponding values will be stored in the file. |
| Optional         |                                                                                                         |
+------------------+---------------------------------------------------------------------------------------------------------+
| **start_time**   | * Filters timescaleDB data by time of polling.                                                          |
| ``string``       | * If this value is not provided, all metric values collected will be stored.                            |
| Optional         |                                                                                                         |
+------------------+---------------------------------------------------------------------------------------------------------+
| **stop_time**    | * Filters timescaleDB data by time of polling.                                                          |
| ``string``       | * If this value is not provided, all metric values collected will be stored.                            |
| Optional         |                                                                                                         |
+------------------+---------------------------------------------------------------------------------------------------------+
| **filename**     | * Target filepath where all timescaleDB will be backed up.                                              |
| ``string``       |                                                                                                         |
| Required         |                                                                                                         |
+------------------+---------------------------------------------------------------------------------------------------------+
To initiate the backup to local file, run the following ansible playbook: ::

    cd utils/timescaledb_utility
    ansible-playbook timescaledb_utility.yml

