View the Kubernetes and Intel Gaudi metrics from the Prometheus UI and Grafana
====================================================================================

Prometheus metrics visualization refers to the process of displaying the metrics collected by the Prometheus exporter in a visual format, enabling easier analysis and interpretation. Using the Prometheus UI and integration with tools like Grafana, users can create custom dashboards, graphs, and charts to visualize metric trends and monitor system health.

**Prerequisites**

* The ``k8s_prometheus_support`` variable in ``input/telemetry_config.yml`` must be ``true``. All the variables and their related information for the config file can be found `here <index.html#id13>`_.
* To enable visualization for the supported Intel Gaudi metrics using Grafana, the ``prometheus_gaudi_support`` and ``visualization_support`` variables in ``input/telemetry_config.yml`` must be set to ``true`` in addition to the above mentioned variable.

**Execute the telemetry playbook**

With the above mentioned variable values provided to the ``input/telemetry_config.yml`` file, execute the ``telemetry.yml`` playbook using the below command: ::

    cd telemetry
    ansible-playbook telemetry.yml -i <inventory filepath>

.. note:: The provided inventory file must contain a ``kube_control_plane``, one or many ``kube_node``, and an ``etcd`` node.

Accessing the Prometheus server for Kubernetes and Gaudi metrics
------------------------------------------------------------------

**Access the Prometheus server from the Kube control plane or kube node**

1. After you have executed the ``telemetry.yml`` playbook, run the following command to bring up all the services that are currently running on the Kubernetes cluster: ::

    kubectl get svc -A

2. Locate the ``prometheus-kube-prometheus-prometheus`` service under the ``monitoring`` namespace. You can access the Prometheus server with the corresponding ``CLUSTER-IP`` of the Prometheus service.

**Access the Prometheus server from the Omnia control plane**

3. After you have executed the ``telemetry.yml`` playbook, run the following command to bring up all the services that are currently running on the Kubernetes cluster: ::

    kubectl get svc -A

4. Locate the ``prometheus-kube-prometheus-prometheus`` service under the ``monitoring`` namespace.

5. Update the Prometheus service ``TYPE``:

    - Use the following command to change the Prometheus service type to ``LoadBalancer`` and assign an ``EXTERNAL-IP``: ::

        kubectl patch service prometheus-kube-prometheus-prometheus -n monitoring -p '{"spec": {"type": "LoadBalancer"}}'

    - Or, use the following command to change the Prometheus service type to ``NodePort``: ::

        kubectl patch service prometheus-kube-prometheus-prometheus -n monitoring -p '{"spec": {"type": "NodePort"}}'

6. To access the Prometheus server from any browser, you can use ``<EXTERNAL IP>:9090`` from the ``kube_control_plane``, or ``<Kube Node IP>:<Kube Node port>`` from the ``kube_node``.

Visualize the Prometheus metrics using Grafana
-------------------------------------------------

1. Find the IP address of the Grafana service using ``kubectl get svc -n grafana``

  .. image:: ../images/grafanaIP.png

2. Login to the Grafana UI by connecting to the cluster IP of grafana service obtained above via port 5000, that's ``http://xx.xx.xx.xx:5000/login``

  .. image:: ../images/Grafana_login.png

3. Add the Prometheus data source to Grafana

  .. image:: ../images/Prometheus_datasource.png

4. Add the Prometheus server URL to the datasource configuration window, for example - ``http://10.50.3.101:9090``

  .. image:: ../images/Prometheus_datasource2.png

5. Click ``Save & test``. A green checkbox pops up signifying successful configuration of the Prometheus datasource.

6. From the dashboard menu on the left, create a dashboard with your own settings or import an existing one from `Grafana dashboards <https://grafana.com/grafana/dashboards/>`_. Set the datasource to ``Prometheus`` while configuring the dashboard. For more information on how to import dashboards, `click here <https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/import-dashboards/>`_

7. Click ``Load`` to bring up the Grafana dashboard with the Prometheus metrics.