Telemetry and visualizations
------------------------------

The telemetry role allows users to set up iDRAC telemetry support and visualizations.

To initiate telemetry support, fill out the following parameters in ``omnia/input/telemetry_config.yml``:

.. csv-table:: Parameters
   :file: ../../Tables/telemetry_config.csv
   :header-rows: 1
   :keepspace:

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
    * `Parallel Coordinates <ParallelCoordinates.html>`_
    * `Sankey Layout <SankeyLayout.html>`_
    * `Spiral Layout <SpiralLayout.html>`_
    * `Power Map <PowerMap>`_


.. note:: The timestamps used for the time metric are based on the timezone set in ``input/provision_config.yml``. In the event of a mismatch between the timezone on the browser being used to access Grafana UI and the timezone in ``input/provision_config.yml``, the time range being used to filter information on the Grafana UI will have to be adjusted per the timezone in ``input/provision_config.yml``.

.. toctree::
    :hidden:
    ParallelCoordinates
    SankeyLayout
    SpiralLayout
    PowerMap




