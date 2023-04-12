Parallel coordinates
--------------------

Parallel coordinates are a great way to visualize multiple metric dimensions simultaneously to see trends and spot outlier activity. Metrics like CPU temp, Fan Speed, Memory Usage etc. can be added or removed as an additional vertical axis. This implementation of parallel coordinate graphing includes a display of metric value distribution in the form of a violin plot along vertical axes and the ability to interact with the graph to perform filtering. Metric range filtering on one or more axes automatically filters the node and sample list in the top left-hand panel to the nodes and samples that fit the filtering criteria.


.. image:: ../../images/Visualization/ParallelCoordinates_InitialView_Collapsed.png

In the above image, both left-hand panels are collapsed to allow for a better view of the graph. They can be expanded by clicking on the arrows highlighted in the picture. The expanded panels can be used to customize the graph.

.. image:: ../../images/Visualization/ParallelCoordinates_InitialView_Expanded.png

In the above image, both left-hand panels are expanded and can be minimized by clicking on the minimize arrows on the right of each panel. These panels can be used to customize the graphs by:

* Filtering by node and node metrics
* Assigning colors to different node metrics

.. image:: ../../images/Visualization/ParallelCoordinates_Recoloration.png

In the above image, the metric **Power Consumption** has been assigned a color to highlight the metric.

.. image:: ../../images/Visualization/ParallelCoordinates_NodeSelection.png

In the above image, data has been filtered by **Node** to get insights into different metrics about specific nodes.

.. image:: ../../images/Visualization/ParallelCoordinates_TopLeftPanel_NodeHighlight.png

In the above image, data for a single node has been highlighted using the top-left panel.

.. image:: ../../images/Visualization/ParallelCoordinates_MetricFiltering.png

In the above image, metric filters were applied on **Power Consumption** by clicking on the vertical axis and dragging a filter box over the range of values required. The top left panel will display nodes and samples that fit the filter. Filters are removed by clicking on the vertical dimension axis again.

.. image:: ../../images/Visualization/ParallelCoordinates_DoubleMetricFiltering.png

In the above image, metric filters were applied on **Power Consumption** and **NIC temperature** . Using more than one filter will result in fewer nodes and telemetry samples that meet the filtering criteria.

.. image:: ../../images/Visualization/ParallelCoordinates_TimeFiltering.png

In the above image, the top-right panel was used to filter data by time, this can be done in 2 ways:

* In absolute yyyy-mm-dd hh:mm:ss format

* In relative time periods such as 'last 5 minutes', 'last 7 days' etc.
