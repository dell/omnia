Logging
=========

Control plane logs
---------------------------

All log files can be viewed via the Dashboard tab ( |Dashboard| ) on the grafana UI. The default dashboard displays ``omnia.log`` and ``syslog``. Custom dashboards can be created per user requirements.

Below is a list of all logs available to Loki and can be accessed on the dashboard:

.. csv-table:: Parameters
   :file: ../Tables/ControlPlaneLogs.csv
   :header-rows: 1
   :keepspace:

.. image:: ../images/Grafana_Loki_TG.png

Provisioning logs
--------------------

Logs pertaining to provisioning can be viewed in ``/var/log/xcat/cluster.log`` on the control plane.

Logs of individual containers
--------------------------------------------
   1. A list of namespaces and their corresponding pods can be obtained using:
      ``kubectl get pods -A``
   2. Get a list of containers for the pod in question using:
      ``kubectl get pods <pod_name> -o jsonpath='{.spec.containers[*].name}'``
   3. Once you have the namespace, pod and container names, run the below command to get the required logs:
      ``kubectl logs pod <pod_name> -n <namespace> -c <container_name>``

Grafana Loki
--------------

    i. Get the Grafana IP using ``kubectl get svc -n grafana``.

    ii. Login to the Grafana UI by connecting to the cluster IP of grafana service via port 5000. That is ``http://xx.xx.xx.xx:5000/login``.

    iii. In the Explore page, select **control-plane-loki**.

    .. image:: ../images/Grafana_Loki.png

    iv. The log browser allows users to filter logs by job, node, user, etc.
        Ex: ::

            (job= "cluster deployment logs") |= "nodename"
            (job="compute log messages") |= "nodename" |="node_username"



.. |Dashboard| image:: ../images/Visualization/DashBoardIcon.png
    :height: 25px
