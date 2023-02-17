Viewing Performance Stats on Grafana
++++++++++++++++++++++++++++++++++++

Using `Texas Technical University data visualization lab <https://idatavisualizationlab.github.io/HPCC>`_, data polled from iDRAC and Slurm can be processed to generate live graphs. These Graphs can be accessed on the Grafana UI.

Once ``provision.yml`` is executed and Grafana is set up, use ``telemetry.yml`` to initiate the Graphs. Data polled via Slurm and iDRAC is streamed into internal databases. This data is processed to create the 4 graphs listed below.


.. note:: This feature only works on Nodes using iDRACs with a datacenter license running a minimum firmware of 4.0.

All your data in a glance
-------------------------

Using the following graphs, data can be visualized to gather correlational information.

.. toctree::
    Parallel Coordinates
    Sankey Layout
    Spiral Layout
    Power Map

