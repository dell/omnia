Telemetry
----------

The telemetry role allows users to set up iDRAC telemetry support and visualizations.

To initiate telemetry support, fill out the following parameters in ``omnia/input/telemetry_config.yml``:

+-------------------------+------------------------------------------+-----------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Name                    | Default, accepted values                 | Required? | Purpose                                                                                                                                                     |
+=========================+==========================================+===========+=============================================================================================================================================================+
| idrac_telemetry_support | **true**, false                          | Required  | Enables iDRAC telemetry support and visualizations.                                                                                                         |
+-------------------------+------------------------------------------+-----------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| slurm_telemetry_support | **true**, false                          | Required  | Enables slurm telemetry support and visualizations.                                                                                                         |
+-------------------------+------------------------------------------+-----------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| timescaledb_name        | telemetry_metrics                        | Optional  | Postgres DB name with timescale extension is used for storing iDRAC and   slurm telemetry metrics.                                                          |
+-------------------------+------------------------------------------+-----------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| mysqldb_name            | idrac_telemetrysource_services_db        | Optional  | MySQL DB name used to store IPs and credentials of iDRACs having   datacenter license                                                                       |
+-------------------------+------------------------------------------+-----------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| timezone                | **GMT**, EST, CET, MST, CST6CDT, PST8PDT | Optional  | This is the timezone that will be set during provisioning of OS. Accepted   values are listed in ``telemetry/common/files/timezone.txt``                    |
+-------------------------+------------------------------------------+-----------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| timescaledb_user        |                                          | Required  | Username used for to authenticate to timescale db. The username must not   contain -,\, ',". The Length of the username should be at least 2   characters.  |
+-------------------------+------------------------------------------+-----------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| timescaledb_password    |                                          | Required  | Password used for to authenticate to timescale db. The username must not   contain -,\, ',". The Length of the username should be at least 2   characters.  |
+-------------------------+------------------------------------------+-----------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| mysqldb_user            |                                          | Required  | Username used for to authenticate to mysql db. The username must not   contain -,\, ',". The Length of the username should be at least 2   characters.      |
+-------------------------+------------------------------------------+-----------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| mysqldb_password        |                                          | Required  | Password used for to authenticate to mysql db. The username must not   contain -,\, ',". The Length of the username should be at least 2   characters.      |
+-------------------------+------------------------------------------+-----------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| mysqldb_root_password   |                                          | Required  | Root password used for to authenticate to mysql db. The username must not   contain -,\, ',". The Length of the username should be at least 2   characters. |
+-------------------------+------------------------------------------+-----------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| idrac_username          |                                          | Optional  | The username for idrac. The username must not contain -,\, ',".   Required only if idrac_telemetry_support is true.                                         |
+-------------------------+------------------------------------------+-----------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| idrac_password          |                                          | Optional  | The password for idrac. The username must not contain -,\, ',".   Required only if idrac_telemetry_support is true.                                         |
+-------------------------+------------------------------------------+-----------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| grafana_username        |                                          | Required  | The username for grafana UI. The length of username should be at least 5.   The username must not contain -,\, ',".                                         |
+-------------------------+------------------------------------------+-----------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| grafana_password        |                                          | Required  | The password for grafana UI. The length of username should be at least 5.   The username must not contain -,\, ',". 'admin' is not an accepted   value.     |
+-------------------------+------------------------------------------+-----------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| node_password           |                                          | Optional  | Password of manager node. Required only if ``slurm_telemetry_support`` is   true.                                                                           |
+-------------------------+------------------------------------------+-----------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+


Once ``control_plane.yml`` and ``omnia.yml`` are executed, run the following commands from ``omnia/telemetry``: ::

    ansible-playbook telemetry.yml -i inventory

.. note:: The passed inventory should have 3 groups: idrac, manager, compute.

After initiation, new nodes can be added to telemetry by running the following commands from ``omnia/telemetry``: ::

    ansible-playbook add_idrac_node.yml -i inventory

.. note::
    * The passed inventory should have an idrac group.
    * ``telemetry_config.yml``  is encrypted upon executing ``telemetry.yml``. View and edit instructions are provided in the `Troubleshooting Guide <../../Troubleshooting/troubleshootingguide.html>`_
    * If ``idrac_telemetry`` is ``true`` while executing ``telemetry.yml``, **or** while running ``add_idrac_node.yml``, if the inventory passed does not contain an idrac group, idrac telemetry will run on IP’s present under ``/opt/omnia/provisioned_idrac_inventory`` of control plane.

.. toctree::
    Visualizations/index






