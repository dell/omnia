Monitoring
==========

The monitoring roles sets up `Grafana <https://grafana.com/>`_  and `Prometheus <https://prometheus.io/>`_.

**Setting Up Monitoring**

1. To set up monitoring, enter all required variables in ``omnia/input/monitor_config.yml``.

+----------------------------+--------------------------+-----------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Name                       | Default, Accepted Values | Required? | Additional Information                                                                                                                                                                                                                                       |
+============================+==========================+===========+==============================================================================================================================================================================================================================================================+
| docker_username            |                          | FALSE     | Username for Dockerhub account. This will be used for Docker login and a   kubernetes secret will be created and patched to service account in default   namespace.  This kubernetes secret can   be used to pull images from private repositories.          |
+----------------------------+--------------------------+-----------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| docker_password            |                          | FALSE     | Password for Dockerhub account. This field is mandatory if   ``docker_username`` is provided.                                                                                                                                                                |
+----------------------------+--------------------------+-----------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| appliance_k8s_pod_net_cidr | 192.168.0.0/16           |           |  Kubernetes pod network CIDR for   appliance k8s network. Make sure this value does not overlap with any of the   host networks.                                                                                                                             |
+----------------------------+--------------------------+-----------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| grafana_username           |                          |           | The username for grafana UI. The length of username should be at least 5   characters. The username must not contain -,\, ',"                                                                                                                                |
+----------------------------+--------------------------+-----------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| grafana_password           |                          |           | Password used for grafana UI. The length of the password should be at   least 5 characters. The password must not contain -,\, ',". Do not use   "admin" in this field.                                                                                      |
+----------------------------+--------------------------+-----------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| mount_location             |                          |           | The path where the Grafana persistent volume will be mounted.  If telemetry is set up, all telemetry   related files will also be stored and both timescale and mysql databases will   be mounted to this location. '/' is mandatory at the end of the path. |
+----------------------------+--------------------------+-----------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

2. Run the playbook using the following command:

``ansible-playbook omnia/monitor/monitor.yml``