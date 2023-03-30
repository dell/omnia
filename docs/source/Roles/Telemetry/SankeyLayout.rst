Sankey Layout
=============

Sankey layout is a multi-factor visualization that incorporates compute
node and hardware telemetry metrics with related job and user
information from the slurm job scheduler. The horizontal Sankey graph
displays relative user usage of the compute or core (selectable)
resources over the time-range selected. Interacting with the graph by
hovering or clicking will bring up job and compute/core related info and
display pie charts and specific metric behavior graphs in the optional
left-hand panel.

Given the amount of data that a Sankey Viewer uses for its display, it does not refresh automatically every 5 seconds. To refresh the view, refresh the page manually.

|img.png|

In the above image, the left panel can be
expanded to customize the view and get more information on selected
Nodes/Jobs/Users.

|image1|

In the above image, the left panel is expanded to
view customization options like:
* Nodes vs Cores
* Color Coding
* Sankey Thickness
* Zoom

|image2|

In the above image, the **Edit** option from the dropdown under the view name (In this case, Sankey) is used to toggle anonymity for usernames in the visualization.

|image3|

In the above image, hovering over the graph has displayed user, job id, compute (or core) id, and job start/stop information. Click on the graph to toggle between freezing and un-freezing the view for point-in-time information.

|image4|

In the above image, the view is zoomed into using a mouse scroll forward. The graph has been customized using the left panel to display the number of cores used by user11.

.. |img.png| image:: ../../../images/Visualization/SankeyLayout_InitialView.png
.. |image1| image:: ../../../images/Visualization/SankeyLayout_LeftPanel.png
.. |image2| image:: ../../../images/Visualization/SankeyLayout_EditMode.png
.. |image3| image:: ../../../images/Visualization/SankeyLayout_HoverFreeze.png
.. |image4| image:: ../../../images/Visualization/SankeyLayout_Zoom.png
