Troubleshooting Guide
============================

Control plane logs
---------------------------

All log files can be viewed via the Dashboard tab ( |Dashboard| ). The Default Dashboard displays ``omnia.log`` and ``syslog``. Custom dashboards can be created per user requirements.

Below is a list of all logs available to Loki and can be accessed on the dashboard:


+------------------------+---------------------------------------------+------------------------------+--------------------------------------------------------------------------------------------------------------------------------+
| Name                   | Location                                    | Purpose                      | Additional   Information                                                                                                       |
+========================+=============================================+==============================+================================================================================================================================+
| Omnia   Logs           | /var/log/omnia.log                          | Omnia Log                    | This log is configured by   Default. This log can be used to track all changes made by all playbooks in   the omnia directory. |
+------------------------+---------------------------------------------+------------------------------+--------------------------------------------------------------------------------------------------------------------------------+
| Accelerator Logs       | /var/log/omnia/accelerator.log              | Accelerator Log              | This log is configured by Default                                                                                              |
+------------------------+---------------------------------------------+------------------------------+--------------------------------------------------------------------------------------------------------------------------------+
| Monitor Logs           | /var/log/omnia/monitor.log                  | Monitor Log                  | This log is configured by Default                                                                                              |
+------------------------+---------------------------------------------+------------------------------+--------------------------------------------------------------------------------------------------------------------------------+
| Network Logs           | /var/log/omnia/network.log                  | Network Log                  | This log is configured by Default                                                                                              |
+------------------------+---------------------------------------------+------------------------------+--------------------------------------------------------------------------------------------------------------------------------+
| Platform Logs          | /var/log/omnia/platforms.log                | Platform Log                 | This log is configured by Default                                                                                              |
+------------------------+---------------------------------------------+------------------------------+--------------------------------------------------------------------------------------------------------------------------------+
| Provision Logs         | /var/log/omnia/provision.log                | Provision Log                | This log is configured by Default                                                                                              |
+------------------------+---------------------------------------------+------------------------------+--------------------------------------------------------------------------------------------------------------------------------+
| Scheduler Logs         | /var/log/omnia/scheduler.log                | Scheduler Log                | This log is configured by Default                                                                                              |
+------------------------+---------------------------------------------+------------------------------+--------------------------------------------------------------------------------------------------------------------------------+
| Security Logs          | /var/log/omnia/security.log                 | Security Log                 | This log is configured by Default                                                                                              |
+------------------------+---------------------------------------------+------------------------------+--------------------------------------------------------------------------------------------------------------------------------+
| Storage Logs           | /var/log/omnia/storage.log                  | Storage Log                  | This log is configured by Default                                                                                              |
+------------------------+---------------------------------------------+------------------------------+--------------------------------------------------------------------------------------------------------------------------------+
| Telemetry Logs         | /var/log/omnia/telemetry.log                | Telemetry Log                | This log is configured by Default                                                                                              |
+------------------------+---------------------------------------------+------------------------------+--------------------------------------------------------------------------------------------------------------------------------+
| Utils Logs             | /var/log/omnia/utils.log                    | Utils Log                    | This log is configured by Default                                                                                              |
+------------------------+---------------------------------------------+------------------------------+--------------------------------------------------------------------------------------------------------------------------------+
| Cluster Utilities Logs | /var/log/omnia/utils_cluster.log            | Cluster Utils Log            | This log is configured by Default                                                                                              |
+------------------------+---------------------------------------------+------------------------------+--------------------------------------------------------------------------------------------------------------------------------+
| syslogs                | /var/log/messages                           | System Logging               | This log is configured by   Default                                                                                            |
+------------------------+---------------------------------------------+------------------------------+--------------------------------------------------------------------------------------------------------------------------------+
| Audit   Logs           | /var/log/audit/audit.log                    | All Login Attempts           | This log is configured by   Default                                                                                            |
+------------------------+---------------------------------------------+------------------------------+--------------------------------------------------------------------------------------------------------------------------------+
| CRON   logs            | /var/log/cron                               | CRON Job Logging             | This log is configured by   Default                                                                                            |
+------------------------+---------------------------------------------+------------------------------+--------------------------------------------------------------------------------------------------------------------------------+
| Pods   logs            | /var/log/pods/ * / * / * log                | k8s pods                     | This log is configured by   Default                                                                                            |
+------------------------+---------------------------------------------+------------------------------+--------------------------------------------------------------------------------------------------------------------------------+
| Access   Logs          | /var/log/dirsrv/slapd-<Realm   Name>/access | Directory Server Utilization | This log is available when   FreeIPA or 389ds is set up ( ie when enable_security_support is set to   ‘true’)                  |
+------------------------+---------------------------------------------+------------------------------+--------------------------------------------------------------------------------------------------------------------------------+
| Error   Log            | /var/log/dirsrv/slapd-<Realm   Name>/errors | Directory Server Errors      | This log is available when   FreeIPA or 389ds is set up ( ie when enable_security_support is set to   ‘true’)                  |
+------------------------+---------------------------------------------+------------------------------+--------------------------------------------------------------------------------------------------------------------------------+
| CA   Transaction Log   | /var/log/pki/pki-tomcat/ca/transactions     | FreeIPA PKI Transactions     | This log is available when   FreeIPA or 389ds is set up ( ie when enable_security_support is set to   ‘true’)                  |
+------------------------+---------------------------------------------+------------------------------+--------------------------------------------------------------------------------------------------------------------------------+
| KRB5KDC                | /var/log/krb5kdc.log                        | KDC Utilization              | This log is available when   FreeIPA or 389ds is set up ( ie when enable_security_support is set to   ‘true’)                  |
+------------------------+---------------------------------------------+------------------------------+--------------------------------------------------------------------------------------------------------------------------------+
| Secure   logs          | /var/log/secure                             | Login Error Codes            | This log is available when   FreeIPA or 389ds is set up ( ie when enable_security_support is set to   ‘true’)                  |
+------------------------+---------------------------------------------+------------------------------+--------------------------------------------------------------------------------------------------------------------------------+
| HTTPD   logs           | /var/log/httpd/ *                           | FreeIPA API Calls            | This log is available when   FreeIPA or 389ds is set up ( ie when enable_security_support is set to   ‘true’)                  |
+------------------------+---------------------------------------------+------------------------------+--------------------------------------------------------------------------------------------------------------------------------+
| DNF   logs             | /var/log/dnf.log                            | Installation Logs            | This log is configured on Rocky   OS                                                                                           |
+------------------------+---------------------------------------------+------------------------------+--------------------------------------------------------------------------------------------------------------------------------+
| Zypper   Logs          | /var/log/zypper.log                         | Installation Logs            | This log is configured on Leap   OS                                                                                            |
+------------------------+---------------------------------------------+------------------------------+--------------------------------------------------------------------------------------------------------------------------------+
| BeeGFS   Logs          | /var/log/beegfs-client.log                  | BeeGFS Logs                  | This log is configured on   BeeGFS client nodes.                                                                               |
+------------------------+---------------------------------------------+------------------------------+--------------------------------------------------------------------------------------------------------------------------------+

Provisioning logs
--------------------

Logs pertaining to provisioning can be viewed in ``/var/log/xcat/xcat.log`` on the target nodes.

Logs of individual containers
--------------------------------------------
   1. A list of namespaces and their corresponding pods can be obtained using:
      ``kubectl get pods -A``
   2. Get a list of containers for the pod in question using:
      ``kubectl get pods <pod_name> -o jsonpath='{.spec.containers[*].name}'``
   3. Once you have the namespace, pod and container names, run the below command to get the required logs:
      ``kubectl logs pod <pod_name> -n <namespace> -c <container_name>``


Connecting to internal databases
------------------------------------
* TimescaleDB
	* Go inside the pod: ``kubectl exec -it pod/timescaledb-0 -n telemetry-and-visualizations -- /bin/bash``
	* Connect to psql: ``psql -U <postgres_username>``
	* Connect to database: ``< timescaledb_name >``
* MySQL DB
	* Go inside the pod: ``kubectl exec -it pod/mysqldb-n telemetry-and-visualizations -- /bin/bash``
	* Connect to psql: ``psql -U <mysqldb_username> -p <mysqldb_password>``
	* Connect to database: ``USE <mysqldb_name>``

Checking and updating encrypted parameters
-----------------------------------------------

1. Move to the filepath where the parameters are saved (as an example, we will be using ``provision_config.yml``):

      ``cd input/``

2. To view the encrypted parameters: ::

   ansible-vault view provision_config.yml --vault-password-file .provision_vault_key

  3. To edit the encrypted parameters: ::

    ansible-vault edit provision_config.yml --vault-password-file .provision_vault_key


Checking pod status on the control plane
--------------------------------------------
   * Select the pod you need to troubleshoot from the output of ``kubectl get pods -A``
   * Check the status of the pod by running ``kubectl describe pod <pod name> -n <namespace name>``

.. |Dashboard| image:: ../images/Visualization/DashBoardIcon.PNG
    :height: 25px


