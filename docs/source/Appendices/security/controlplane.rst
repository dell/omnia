Enabling Security on the Control Plane
========================================


Omnia uses `FreeIPA (on RockyOS) <https://www.freeipa.org/page/Documentation>`_ to enable security features like authorisation and access control.


**Enabling Authentication on the Control Plane:**



Set the parameter 'enable_security_support' to true in ``provision_config.yml``.



.. note::

    * In the event that ``provision.yml`` fails after executing the control plane security tasks, ``sshd`` services will have to be restarted manually by the User.

    * Once security features are enabled on the control plane, ``/etc/resolv.conf`` will become immutable. To edit the file, run ``chattr -i /etc/resolv.conf`` . To make file immutable after edits, run ``chattr +i /etc/resolv.conf``. Changes made using this method may not be persistent across reboots.

**Limiting User Authentication over sshd**

Users logging into this host can be **optionally** allowed or denied using an access control list. All users to be allowed or denied are to be listed in the variable ``user`` in ``security_vars.yml``.

.. note:: All users on the server will have to be defined manually. Omnia does not create any users by default.

**Session Timeout**

To encourage security, users who have been idle over 3 minutes will be logged out automatically. To adjust this value, update the ``session_timeout`` variable in ``security_vars.yml``. This variable is mandatory.

**Restricting Program Support**

Optionally, different communication protocols can be disabled on the control plane using the ``restrict_program_support`` and ``restrict_softwares`` variables. These protocols include: telnet,lpd,bluetooth,rlogin and rexec. Features that cannot be disabled include: ftp,smbd,nmbd,automount and portmap.

.. note:: The parameter ``restrict_softwares`` is **case-sensitive**

**Logging Program Executions using Snoopy**

Omnia installs Snoopy to log all program executions on Linux/BSD systems. For more information on Snoopy, `click here <https://github.com/a2o/snoopy>`_.

**Logging User activity using PSACCT/ACCT**

Using PSACCT on Rocky and Acct on LeapOS, admins can monitor activity. For more information, click `here <https://www.redhat.com/sysadmin/linux-system-monitoring-acct>`_.

**Configuring Email Alerts for Authentication Failures**

If the ``alert_email_address`` variable in ``security_config.yml`` is populated with a single, valid email ID, all authentication failures will trigger an email notification. A cron job is set up to verify failures and send emails every hour.

.. note:: The ``alert_email_address`` variable is **optional**. If it is not populated, authentication failure email alerts will be disabled.

**Log Aggregation via Grafana**

`Loki <https://grafana.com/docs/loki/latest/fundamentals/overview/>`_ is a datastore used to efficiently hold log data for security purposes. Using the ``promtail`` agent, logs are collated and streamed via an HTTP API.

.. note:: When ``provision.yml`` is run, Loki is automatically set up as a data source on the Grafana UI.

**Querying Loki**

Loki uses basic regex based syntax to filter for specific jobs, dates or timestamps.

    * Select the Explore |Explore|  tab to select control-plane-loki from the drop-down.

    * Using `LogQL queries <https://grafana.com/docs/loki/latest/logql/log_queries/>`_, all logs in ``/var/log`` can be accessed using filters (Eg: ``{job=???Omnia???}`` )

**Viewing Logs on the Dashboard**

All log files can be viewed via the Dashboard tab ( |Dashboard| ). The Default Dashboard displays ``omnia.log`` and ``syslog``. Custom dashboards can be created per user requirements.

Below is a list of all logs available to Loki and can be accessed on the dashboard:


+---------------------------+------------------------------------------------------------------------------+------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------+
| Name                      | Location                                                                     | Purpose                      | Additional Information                                                                                                                             |
+===========================+==============================================================================+==============================+====================================================================================================================================================+
| Omnia Logs                | /var/log/omnia.log                                                           | Omnia Log                    | This log is configured by Default. This log can be used to track all changes made by all playbooks in the ``omnia`` directory.                     |
+---------------------------+------------------------------------------------------------------------------+------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------+
| Omnia Control Plane       | /var/log/omnia_control_plane.log                                             | Control plane Log            | This log is configured by Default. This log can be used to track all changes made by all playbooks in the ``control_plane`` directory.       |
+---------------------------+------------------------------------------------------------------------------+------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------+
| Omnia Telemetry           | /var/log/omnia/omnia_telemetry.log                                           | Telemetry Log                | This log is configured by Default. This log can be used to track all changes made by all playbooks in the ``omnia/telemetry`` directory.           |
+---------------------------+------------------------------------------------------------------------------+------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------+
| Omnia Tools               | /var/log/omnia/omnia_tools.log                                               | Tools Log                    | This log is configured by Default. This log can be used to track all changes made by all playbooks in the ``omnia/tools`` directory.               |
+---------------------------+------------------------------------------------------------------------------+------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------+
| Omnia Platforms           | /var/log/omnia/omnia_platforms.log                                           | Platforms Log                | This log is configured by Default. This log can be used to track all changes made by all playbooks in the ``omnia/platforms`` directory.           |
+---------------------------+------------------------------------------------------------------------------+------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------+
| Omnia Control Plane Tools | /var/log/omnia/omnia_control_plane_tools.log                                 | Control Plane tools logs     | This log is configured by Default. This log can be used to track all changes made by all playbooks in the ``omnia/control_plane/tools`` directory. |
+---------------------------+------------------------------------------------------------------------------+------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------+
| Node Info CLI log         | /var/log/omnia/collect_node_info/collect_node_info_yyyy-mm-dd-HHMMSS.log     | CLI Log                      | This log is configured when AWX is disabled. This log can be used to track scheduled and unscheduled node inventory jobs initiated by CLI.         |
+---------------------------+------------------------------------------------------------------------------+------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------+
| Device Info CLI log       | /var/log/omnia/collect_device_info/collect_device_info_yyyy-mm-dd-HHMMSS.log | CLI Log                      | This log is configured when AWX is disabled. This log can be used to track scheduled and unscheduled device inventory jobs initiated by CLI.       |
+---------------------------+------------------------------------------------------------------------------+------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------+
| iDRAC CLI log             | /var/log/omnia/idrac/idrac-yyyy-mm-dd-HHMMSS.log                             | CLI Log                      | This log is configured when AWX is disabled. This log can be used to track iDRAC jobs initiated by CLI.                                            |
+---------------------------+------------------------------------------------------------------------------+------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------+
| Infiniband CLI log        | //var/log/omnia/infiniband/infiniband-yyyy-mm-dd-HHMMSS.log                  | CLI Log                      | This log is configured when AWX is disabled. This log can be used to track Infiniband jobs initiated by CLI.                                       |
+---------------------------+------------------------------------------------------------------------------+------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------+
| Ethernet CLI log          | /var/log/omnia/ethernet/ethernet-yyyy-mm-dd-HHMMSS.log                       | CLI Log                      | This log is configured when AWX is disabled. This log can be used to track Ethernet jobs initiated by CLI.                                         |
+---------------------------+------------------------------------------------------------------------------+------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------+
| Powervault CLI log        | /var/log/omnia/powervault/powervault-yyyy-mm-dd-HHMMSS.log                   | CLI Log                      | This log is configured when AWX is disabled. This log can be used to track Powervault jobs initiated by CLI.                                       |
+---------------------------+------------------------------------------------------------------------------+------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------+
| syslogs                   | /var/log/messages                                                            | System Logging               | This log is configured by Default                                                                                                                  |
+---------------------------+------------------------------------------------------------------------------+------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------+
| Audit Logs                | /var/log/audit/audit.log                                                     | All Login Attempts           | This log is configured by Default                                                                                                                  |
+---------------------------+------------------------------------------------------------------------------+------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------+
| CRON logs                 | /var/log/cron                                                                | CRON Job Logging             | This log is configured by Default                                                                                                                  |
+---------------------------+------------------------------------------------------------------------------+------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------+
| Pods logs                 | /var/log/pods/ * / * / * log                                                 | k8s pods                     | This log is configured by Default                                                                                                                  |
+---------------------------+------------------------------------------------------------------------------+------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------+
| Access Logs               | /var/log/dirsrv/slapd-<Realm Name>/access                                    | Directory Server Utilization | This log is available when FreeIPA or 389ds is set up ( ie when   enable_security_support is set to 'true')                                        |
+---------------------------+------------------------------------------------------------------------------+------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------+
| Error Log                 | /var/log/dirsrv/slapd-<Realm Name>/errors                                    | Directory Server Errors      | This log is available when FreeIPA or 389ds is set up ( ie when   enable_security_support is set to 'true')                                        |
+---------------------------+------------------------------------------------------------------------------+------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------+
| CA Transaction Log        | /var/log/pki/pki-tomcat/ca/transactions                                      | FreeIPA PKI Transactions     | This log is available when FreeIPA or 389ds is set up ( ie when   enable_security_support is set to 'true')                                        |
+---------------------------+------------------------------------------------------------------------------+------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------+
| KRB5KDC                   | /var/log/krb5kdc.log                                                         | KDC Utilization              | This log is available when FreeIPA or 389ds is set up ( ie when   enable_security_support is set to 'true')                                        |
+---------------------------+------------------------------------------------------------------------------+------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------+
| Secure logs               | /var/log/secure                                                              | Login Error Codes            | This log is available when FreeIPA or 389ds is set up ( ie when   enable_security_support is set to 'true')                                        |
+---------------------------+------------------------------------------------------------------------------+------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------+
| HTTPD logs                | /var/log/httpd/ *                                                            | FreeIPA API Calls            | This log is available when FreeIPA or 389ds is set up ( ie when   enable_security_support is set to 'true')                                        |
+---------------------------+------------------------------------------------------------------------------+------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------+
| DNF logs                  | /var/log/dnf.log                                                             | Installation Logs            | This log is configured on Rocky OS                                                                                                                 |
+---------------------------+------------------------------------------------------------------------------+------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------+
| Zypper Logs               | /var/log/zypper.log                                                          | Installation Logs            | This log is configured on Leap OS                                                                                                                  |
+---------------------------+------------------------------------------------------------------------------+------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------+
| BeeGFS Logs               | /var/log/beegfs-client.log                                                   | BeeGFS Logs                  | This log is configured on BeeGFS client nodes.                                                                                                     |
+---------------------------+------------------------------------------------------------------------------+------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------+


.. |Dashboard| image:: ../../../images/Visualization/DashBoardIcon.PNG
    :height: 25px

.. |Explore| image:: ../../../images/Visualization/ExploreIcon.PNG
    :height: 25px

