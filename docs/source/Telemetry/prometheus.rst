Visualization of iDRAC telemetry metrics collected by Prometheus
===================================================================

Via Grafana UI
-----------------

1. Log in to the Grafana UI via port 5000. Enter the below URL into the browser's address bar: 

    ::
        
        http://localhost:5000/login

    .. note:: In the above command, instead of ``localhost``, you can also provide the admin IP or public IP address to access the Grafana UI.

2. In the Explore page, select **oim-prometheus** to view the metrics collected by the prometheus metrics exporter.

    .. image:: ../images/Grafana_prometheus.png
        :width: 600px

3. Select the specific metric that you want to view from the **Metric** drop-down menu.

    .. image:: ../images/Grafana_prometheus2.png
        :width: 600px

4. Filter the metrics further using the **Label filters**.

    .. image:: ../images/Grafana_prometheus3.png
        :width: 600px

5. Use the **time filter** to get the metrics for a particular time period.

    .. image:: ../images/Grafana_prometheus4.png
        :width: 600px


Via Prometheus UI
-------------------

1. To access the Prometheus UI via port 9090, enter the below URL into the browser's address bar: 
    
    ::
        
        http://localhost:9090

    .. note:: In the above command, instead of ``localhost``, you can also provide the admin IP or public IP address to access the Grafana UI.

    .. image:: ../images/idrac_telemetry_prometheus_ui.png
        :width: 600px

2. Open the metrics explorer to view the list of metrics collected by the prometheus metrics exporter.

    .. image:: ../images/idrac_telemetry_prometheus_ui2.png
        :width: 600px

3. Select the specific metric that you want to view and then click **Execute**.

    .. image:: ../images/idrac_telemetry_prometheus_ui3.png
        :width: 600px

4. To view the metric values as a graph, select the **Graph** button.

    .. image:: ../images/idrac_telemetry_prometheus_ui4.png
        :width: 600px