Telemetry
----------

The telemetry role allows users to set up iDRAC telemetry support and visualizations.

To initiate telemetry support, fill out the following parameters in ``omnia/input/telemetry_config.yml``:

+-------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Name                    | Description                                                                                                                                                 |
+=========================+=============================================================================================================================================================+
| idrac_telemetry_support | Enables iDRAC telemetry support and visualizations.                                                                                                         |
|      ``boolean``        |                                                                                                                                                             |
|      Required           |      **Values**                                                                                                                                             |
|                         |      * ``true`` <- Default                                                                                                                                  |
|                         |      * ``false``                                                                                                                                            |
+-------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| slurm_telemetry_support | Enables slurm telemetry support and visualizations.                                                                                                         |
|      ``boolean``        |                                                                                                                                                             |
|      Required           |      **Values**                                                                                                                                             |
|                         |      * ``true`` <- Default                                                                                                                                  |
|                         |      * ``false``                                                                                                                                            |
+-------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| timescaledb_name        | Postgres DB name with timescale extension is used for storing iDRAC and   slurm telemetry metrics.                                                          |
|      ``string``         |                                                                                                                                                             |
|      Optional           |      **Default values**: telemetry_metrics                                                                                                                  |
+-------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| mysqldb_name            | MySQL DB name used to store IPs and credentials of iDRACs having   datacenter license                                                                       |
|      ``string``         |                                                                                                                                                             |
|      Optional           |      **Default values**: idrac_telemetrysource_services_db                                                                                                  |
+-------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| timezone                | This is the timezone that will be set during provisioning of OS. Accepted   values are listed in ``telemetry/common/files/timezone.txt``.                   |
|      ``string``         |                                                                                                                                                             |
|      Optional           |      **Default values**: GMT                                                                                                                                |
+-------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| timescaledb_user        | Username used for to authenticate to timescale db. The username must not   contain -,\, ',". The Length of the username should be at least 2   characters.  |
|      ``string``         |                                                                                                                                                             |
|      Required           |                                                                                                                                                             |
+-------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| timescaledb_password    | Password used for to authenticate to timescale db. The username must not   contain -,\, ',". The Length of the username should be at least 2   characters.  |
|      ``string``         |                                                                                                                                                             |
|      Required           |                                                                                                                                                             |
+-------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| mysqldb_user            | Username used for to authenticate to mysql db. The username must not   contain -,\, ',". The Length of the username should be at least 2   characters.      |
|      ``string``         |                                                                                                                                                             |
|      Required           |                                                                                                                                                             |
+-------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| mysqldb_password        | Password used for to authenticate to mysql db. The username must not   contain -,\, ',". The Length of the username should be at least 2   characters.      |
|      ``string``         |                                                                                                                                                             |
|      Required           |                                                                                                                                                             |
+-------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| mysqldb_root_password   | Root password used for to authenticate to mysql db. The username must not   contain -,\, ',". The Length of the username should be at least 2   characters. |
|      ``string``         |                                                                                                                                                             |
|      Required           |                                                                                                                                                             |
+-------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| idrac_username          | The username for iDRAC. The username must not contain -,\, ',".   Required only if idrac_telemetry_support is true.                                         |
|      ``string``         |                                                                                                                                                             |
|      Optional           |                                                                                                                                                             |
+-------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| idrac_password          | The password for iDRAC. The username must not contain -,\, ',".   Required only if idrac_telemetry_support is true.                                         |
|      ``string``         |                                                                                                                                                             |
|      Optional           |                                                                                                                                                             |
+-------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| grafana_username        | The username for grafana UI. The length of username should be at least 5.   The username must not contain -,\, ',".                                         |
|      ``string``         |                                                                                                                                                             |
|      Required           |                                                                                                                                                             |
+-------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| grafana_password        | The password for grafana UI. The length of username should be at least 5.   The username must not contain -,\, ',". 'admin' is not an accepted   value.     |
|      ``string``         |                                                                                                                                                             |
|      Required           |                                                                                                                                                             |
+-------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+
| node_password           | Password of manager node. Required only if ``slurm_telemetry_support`` is   true.                                                                           |
|      ``string``         |                                                                                                                                                             |
|      Optional           |                                                                                                                                                             |
+-------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------------+

Once ``control_plane.yml`` and ``omnia.yml`` are executed, run the following commands from ``omnia/telemetry``: ::

    ansible-playbook telemetry.yml -i inventory

.. note:: The passed inventory should have 3 groups: idrac, manager, compute.

After initiation, new nodes can be added to telemetry by running the following commands from ``omnia/telemetry``: ::

    ansible-playbook add_idrac_node.yml -i inventory

.. note::
    * The passed inventory should have an idrac group.
    * ``telemetry_config.yml``  is encrypted upon executing ``telemetry.yml``. To edit the file, use ``ansible-vault edit telemetry_config.yml --vault-password-file .telemetry_vault_key``.
    * If ``idrac_telemetry`` is ``true`` while executing ``telemetry.yml``, **or** while running ``add_idrac_node.yml``, if the inventory passed does not contain an idrac group, idrac telemetry will run on IP’s present under ``/opt/omnia/provisioned_idrac_inventory`` of control plane.

Viewing Performance Stats on Grafana
++++++++++++++++++++++++++++++++++++

Using `Texas Technical University data visualization lab <https://idatavisualizationlab.github.io/HPCC>`_, data polled from iDRAC and Slurm can be processed to generate live graphs. These Graphs can be accessed on the Grafana UI.

Once ``provision.yml`` is executed and Grafana is set up, use ``telemetry.yml`` to initiate the Graphs. Data polled via Slurm and iDRAC is streamed into internal databases. This data is processed to create the 4 graphs listed below.

.. note:: This feature only works on Nodes using iDRACs with a datacenter license running a minimum firmware of 4.0.

**To access the grafana UI:**

    i. Find the IP address of the Grafana service using ``kubectl get svc -n grafana``

    .. image:: ../../images/grafanaIP.png

    ii. Login to the Grafana UI by connecting to the cluster IP of grafana service obtained above via port 5000. That is ``http://xx.xx.xx.xx:5000/login``

    .. image:: ../../images/Grafana_login.png

    iii. Enter the ``grafana_username`` and ``grafana_password`` as mentioned in ``monitor/monitor_config.yml``.

    .. image:: ../../images/Grafana_Dashboards.png


**All your data in a glance**:

Using the following graphs, data can be visualized to gather correlational information.

.. toctree::
    ParallelCoordinates
    SankeyLayout
    SpiralLayout
    PowerMap

.. note:: The timestamps used for the time metric are based on the timezone set in ``input/provision_config.yml``. In the event of a mismatch between the timezone on the browser being used to access Grafana UI and the timezone in ``input/provision_config.yml``, the time range being used to filter information on the Grafana UI will have to be adjusted per the timezone in ``input/provision_config.yml``.





