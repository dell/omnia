Telemetry and visualizations
------------------------------

The telemetry feature allows to set up Omnia telemetry and/or iDRAC telemetry

To initiate telemetry support, fill out the following parameters in ``omnia/input/telemetry_config.yml``:

.. csv-table:: Parameters
   :file: ../../Tables/telemetry_config.csv
   :header-rows: 1
   :keepspace:

Once you have executed ``provision.yml`` and has also provisioned the cluster, initiate telemetry on the cluster as part of ``omnia.yml``, which configures the cluster with scheduler, storage and authentication using the below command. ::

    ansible-playbook omnia.yml -i inventory

Optionally, you can initiate only telemetry using the below command: ::

    ansible-playbook telemetry.yml -i inventory

.. note:: Depending on the type of telemetry initiated, the following groups are required. :
    omnia_telemetry: manager, compute
    idrac_telemetry: idrac

After initiation, new iDRACs can be added for ``idrac_telemetry`` acquisition by running the following commands: ::

    ansible-playbook add_idrac_node.yml -i inventory

.. note::
    * The passed inventory should have an idrac group.
    * The passed inventory should have an idrac group, if ``idrac_telemetry_support`` is true.
    * If ``omnia_telemetry_support`` is true, then the inventory should have manager and compute groups along with optional login group.

**Visualizations**

.. toctree::

    Visualizations/index




