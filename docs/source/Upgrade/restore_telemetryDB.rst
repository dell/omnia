Restoring Telemetry database post Omnia upgrade
================================================

After upgrading Omnia, if you want to retain the telemetry data from Omnia v1.5.1, you need to manually restore the telemetry database from the ``backup_location`` configured in `upgrade_config,yml <upgrade.html>`_. Perform the following steps to do so:

1. Copy the backed up telemetry database from the ``backup_location`` configured in ``upgrade_config,yml`` to ``/opt/omnia/telemetry/iDRAC-Referencing-Tools``.

2. Stop the Omnia telemetry services on all the cluster nodes.

3. In order to execute the psql commands, connect to the ``timescaledb`` pod using the following steps:

    * Execute the following command: ::

        kubectl exec -it timescaledb-0 -n telemetry-and-visualizations -- /bin/bash

    * Verify that the dump file is present using the ``ls`` command.

4. Now, connect to the ``telemetry_metrics`` database using the following command: ::

    psql -U omnia

5. Execute the following command to obtain the ``pod_external_ip`` for the timescale database: ::

    kubectl get svc -A output

6. Execute the following command to initiate the database restore operation: ::

    psql --dbname=telemetry_metrics --host=<pod_external_ip> --port=5432 --username=omnia --file=telemetry_tsdb_dump.sql < telemetry_tsdb_dump.sql


Next steps
============

1. Use the following command to see and verify the restored data: ::

    timescaledb-0:/go/src/github.com/telemetry-reference-tools# psql -U omnia

2. Restart the Omnia telemetry services on all the cluster nodes.

3. Check and see if the number of rows have increased in the timescale database. This signifies that the restoration has taken place successfully.

4. Check the status both ``omnia_telemtry.service`` and public ``time_series`` metrics.

5. Restart the node.