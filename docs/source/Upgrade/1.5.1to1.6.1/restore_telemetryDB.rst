Restoring Telemetry database post Omnia upgrade
================================================

After upgrading Omnia, if you want to retain the telemetry data from Omnia v1.5.1, you need to manually restore the telemetry database from the ``telemetry_tsdb_dump.sql`` file. Perform the following steps to do so:

1. Copy the backed up telemetry database file, that is ``telemetry_tsdb_dump.sql``, from the ``backup_location`` to ``/opt/omnia/telemetry/iDRAC-Referencing-Tools``.

2. Stop the Omnia telemetry services on all the cluster nodes. Run the ``telemetry.yml`` playbook after setting the ``idrac_telemetry_support``, ``omnia_telemetry_support``, and ``visualization_support`` parameters to ``false`` in ``input/telemetry_config.yml``. Execute the following command: ::

    cd telemetry
    ansible-playbook telemetry.yml -i ../upgrade/inventory

3. Connect to the ``timescaledb`` pod and execute the psql commands. Perform the following steps:

    * Execute the following command: ::

        kubectl exec -it timescaledb-0 -n telemetry-and-visualizations -- /bin/bash

    * Verify that the dump file is present using the ``ls`` command.

    * Connect to the psql client using the following command: ::

        psql -U <timescaledb_user>

      where "timescaledb_user" is the configured ``timescaledb`` username for telemetry.

    * Drop the current database using the command below: ::

         DROP DATABASE telemetry_metrics;

    .. note:: If there are processes which are preventing you to drop the database, then terminate those processes and try again.

    * Create an empty telemetry database for Omnia v1.6.1 using the command below: ::

         CREATE DATABASE telemetry_metrics;

    * Exit from the psql client using ``\q`` command.

    * Execute the following command to initiate the database restore operation: ::

        psql --dbname=telemetry_metrics --host=<pod_external_ip> --port=5432 --username=<timescaledb_user> -v ON_ERROR_STOP=1 --echo-errors -c "SELECT public.timescaledb_pre_restore();" -f telemetry_tsdb_dump.sql -c "SELECT public.timescaledb_post_restore();"

    .. note:: Execute the following command to obtain the ``pod_external_ip`` and ``port`` for the ``timescaledb`` pod:
        ::
            kubectl get svc -A output

    * Drop the ``insert_block_trigger`` if it exists using the following commands: ::

        psql -U omnia
        \c telemetry_metrics
        DROP TRIGGER IF EXISTS ts_insert_blocker ON public.timeseries_metrics;
        DROP TRIGGER IF EXISTS ts_insert_blocker ON omnia_telemetry.metrics;


Next steps
============

1. Connect to the ``telemetry_metrics`` database and verify if the restored telemetry data is present in ``public.timeseries_metrics`` and ``omnia_telemetry.metrics`` tables.

2. Post verification, you can choose to restart the Omnia telemetry services. Run the ``telemetry.yml`` playbook after modifying the ``input/telemetry_config.yml`` as per your requirements. For more information regarding the telemetry parameters, `click here <../../InstallationGuides/BuildingClusters/schedulerinputparams.html#id18>`_. Execute the following command: ::

    cd telemetry
    ansible-playbook telemetry.yml -i ../upgrade/inventory

3. After telemetry services are enabled, check ``omnia_telemetry.metrics`` and ``public.timeseries_metrics`` tables to see if the number of rows have increased. This signifies that the fresh telemetry data from Omnia v1.6.1 is getting updated in the database.