Control plane logs
-------------------

All log files can be viewed via CLI. Alternatively, most log files can be viewed via the Dashboard tab ( |Dashboard| ) on the grafana UI.

.. caution:: It is not recommended to delete the below log files or the directories they reside in.

.. note:: Log files are rotated periodically as a storage consideration. To customize how often logs are rotated, edit the ``/etc/logrotate.conf`` file on the node.

Below is a list of all logs available to Loki and can be accessed on the dashboard:

.. csv-table:: Log files
   :file: ../Tables/ControlPlaneLogs.csv
   :header-rows: 1
   :keepspace:

.. image:: ../images/Grafana_Loki_TG.png

Logs of individual containers
-------------------------------
   1. A list of namespaces and their corresponding pods can be obtained using:
      ``kubectl get pods -A``
   2. Get a list of containers for the pod in question using:
      ``kubectl get pods <pod_name> -o jsonpath='{.spec.containers[*].name}'``
   3. Once you have the namespace, pod and container names, run the below command to get the required logs:
      ``kubectl logs pod <pod_name> -n <namespace> -c <container_name>``

Provisioning logs
--------------------

Logs pertaining to actions taken during ``provision.yml``  can be viewed in ``/var/log/xcat/cluster.log`` and ``/var/log/xcat/computes.log`` on the control plane.

.. note::  As long as a node has been added to a cluster by Omnia, deployment events taking place on the node will be updated in ``/var/log/xcat/cluster.log``.


Telemetry logs
---------------

Logs pertaining to actions taken by Omnia or iDRAC telemetry can be viewed in ``/var/log/messages``. Each log entry is tagged "omnia_telemetry". Log entries typically follow this format. ::

    <Date time> <Node name> omnia_telemetry[<Process ID>]: <name of file>:<name of method throwing error>: <Error message>


Grafana Loki
--------------

After `telemetry.yml <../Roles/Telemetry/index.html>`_ is run, Grafana services are installed on the control plane.

    i. Get the Grafana IP using ``kubectl get svc -n grafana``.

    ii. Login to the Grafana UI by connecting to the cluster IP of grafana service via port 5000. That is ``http://xx.xx.xx.xx:5000/login``.

    iii. In the Explore page, select **control-plane-loki**.

    .. image:: ../images/Grafana_Loki.png

    iv. The log browser allows users to filter logs by job, node, user, etc.
        Ex: ::

            (job= "cluster deployment logs") |= "nodename"
            (job="compute log messages") |= "nodename" |="node_username"

Custom dashboards can be created per user requirement.

.. |Dashboard| image:: ../images/Visualization/DashBoardIcon.png
    :height: 25px
