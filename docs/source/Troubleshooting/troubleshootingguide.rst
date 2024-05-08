Troubleshooting guide
============================

Connecting to internal databases
------------------------------------
* TimescaleDB
    * Go inside the pod: ``kubectl exec -it pod/timescaledb-0 -n telemetry-and-visualizations -- /bin/bash``
    * Connect to psql: ``psql -U <postgres_username>``
    * Connect to database: ``\c telemetry_metrics``
* MySQL DB
    * Go inside the pod: ``kubectl exec -it pod/mysqldb-0 -n telemetry-and-visualizations -- /bin/bash``
    * Connect to mysql: ``mysql -U <mysqldb_username> -p <mysqldb_password>``
    * Connect to database: ``USE idrac_telemetrysource_services_db``

Checking and updating encrypted parameters
-----------------------------------------------

1. Move to the filepath where the parameters are saved (as an example, we will be using ``provision_config.yml``): ::

    cd input/

2. To view the encrypted parameters: ::

   ansible-vault view provision_config.yml --vault-password-file .provision_vault_key

3. To edit the encrypted parameters: ::

    ansible-vault edit provision_config.yml --vault-password-file .provision_vault_key

Checking pod status on the control plane
--------------------------------------------
   * Select the pod you need to troubleshoot from the output of ``kubectl get pods -A``
   * Check the status of the pod by running ``kubectl describe pod <pod name> -n <namespace name>``

Using telemetry information to diagnose node issues
----------------------------------------------------

.. csv-table:: Regular telemetry metrics
   :file: ../Tables/Metrics_Regular.csv
   :header-rows: 1
   :keepspace:

.. [1] This metric is collected from the manager node if a login node is absent.

.. csv-table:: Health telemetry metrics
   :file: ../Tables/Metrics_Health.csv
   :header-rows: 1
   :keepspace:


.. csv-table:: GPU telemetry metrics
   :file: ../Tables/Metrics_GPU.csv
   :header-rows: 1
   :keepspace:



.. |Dashboard| image:: ../images/Visualization/DashBoardIcon.png
    :height: 25px


