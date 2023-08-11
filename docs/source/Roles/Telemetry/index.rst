Telemetry and visualizations
------------------------------

The telemetry feature allows to set up Omnia telemetry and/or iDRAC telemetry

To initiate telemetry support, fill out the following parameters in ``omnia/input/telemetry_config.yml``:

.. csv-table:: Parameters
   :file: ../../Tables/telemetry_config.csv
   :header-rows: 1
   :keepspace:

Once you have executed ``provision.yml`` and has also provisioned the cluster, initiate telemetry on the cluster along with ``omnia.yml``, which configures the cluster with scheduler, storage and authentication. Optionally, you can initiate only telemetry using the below command: ::

    ansible-playbook telemetry.yml -i inventory

.. note:: The passed inventory should have 3 groups: idrac, manager, compute.

After initiation, new nodes can be added to telemetry by running the following commands from ``omnia/telemetry``: ::

    ansible-playbook add_idrac_node.yml -i inventory

.. note::
    * The passed inventory should have an idrac group.
    * The passed inventory should have an idrac group, if ``idrac_telemetry_support`` is true.
    * If ``omnia_telemetry_support`` is true, then the inventory should have manager and compute groups along with optional login group.


.. toctree::
    Visualizations/index




