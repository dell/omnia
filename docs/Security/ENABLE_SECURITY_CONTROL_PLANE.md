# Enabling Security on the Control Plane

Omnia uses [FreeIPA (on RockyOS)](https://www.freeipa.org/page/Documentation
) and [389ds(on Leap)](https://doc.opensuse.org/documentation/leap/security/html/book-security/cha-security-ldap.html
) to enable security features like authorisation and access control.


## Enabling Authentication on the Control Plane:

Once all [pre-requisites](../PreRequisites/Control_Plane_Security_PreReqs.md) are met, set the parameter 'enable_security_support' to true in `base_vars.yml`

>> __Note:__ 
>> * In the event that `control_plane.yml` fails after executing the control plane security tasks, `sshd` services will have to be restarted manually by the User.
>> * Once security features are enabled on the control plane, `/etc/resolv.conf` will become immutable. To edit the file, run `chattr -i /etc/resolv.conf` . To make file immutable after edits, run `chattr +i /etc/resolv.conf`. Changes made using this method may not be persistent across reboots.
## Limiting User Authentication over sshd

Users logging into this host can be __optionally__ allowed or denied using an access control list. All users to be allowed or denied are to be listed in the variable `user` in `security_vars.yml`. 

>> __Note:__ All users on the server will have to be defined manually. Omnia does not create any users by default.

## Session Timeout

To encourage security, users who have been idle over 3 minutes will be logged out automatically. To adjust this value, update the `session_timeout` variable in `security_vars.yml`. This variable is mandatory. 

## Restricting Program Support

Optionally, different communication protocols can be disabled on the control plane using the `restrict_program_support` and `restrict_softwares` variables. These protocols include: telnet,lpd,bluetooth,rlogin and rexec. Features that cannot be disabled include: ftp,smbd,nmbd,automount and portmap. 

## Logging Program Executions using Snoopy

Omnia installs Snoopy to log all program executions on Linux/BSD systems. For more information on Snoopy, click [here](https://github.com/a2o/snoopy).

## Logging User activity using PSACCT/ACCT

Using PSACCT on Rocky and Acct on LeapOS, admins can monitor activity. For more information, click [here](https://www.redhat.com/sysadmin/linux-system-monitoring-acct).

## Configuring Email Alerts for Authentication Failures

If the `alert_email_address` variable in `security_config.yml` is populated with a single, valid email ID, all authentication failures will trigger an email notification. A cron job is set up to verify failures and send emails every hour.

>> __Note:__ The `alert_email_address` variable is __optional__. If it is not populated, authentication failure email alerts will be disabled.

## Log Aggregation via Grafana

[Loki](https://grafana.com/docs/loki/latest/fundamentals/overview/) is a datastore used to efficiently hold log data for security purposes. Using the `promtail` agent, logs are collated and streamed via a HTTP API.

>> __Note:__ When `control_plane.yml` is run, Loki is automatically set up as a data source on the Grafana UI.



### Querying Loki 

Loki uses basic regex based syntax to filter for specific jobs, dates or timestamps.

* Select the Explore ![Explore Icon](../Telemetry_Visualization/Images/ExploreIcon.PNG) tab to select control-plane-loki from the drop down.
* Using [LogQL queries](https://grafana.com/docs/loki/latest/logql/log_queries/), all logs in `/var/log` can be accessed using filters (Eg: `{job=???Omnia???}` )

## Viewing Logs on the Dashboard

All log files can be viewed via the Dashboard tab (![Dashboard Icon](../Telemetry_Visualization/Images/DashBoardIcon.PNG)). The Default Dashboard displays `omnia.log` and `syslog`. Custom dashboards can be created per user requirements.

Below is a list of all logs available to Loki and can be accessed on the dashboard:

| Name               | Location                                  | Purpose                      | Additional Information                                                                             |
|--------------------|-------------------------------------------|------------------------------|----------------------------------------------------------------------------------------------------|
| Omnia Logs         | /var/log/omnia.log                        | Omnia Log                    | This log is configured by Default                                                                  |
| syslogs            | /var/log/messages                         | System Logging               | This log is configured by Default                                                                  |
| Audit Logs         | /var/log/audit/audit.log                  | All Login Attempts           | This log is configured by Default                                                                  |
| CRON logs          | /var/log/cron                             | CRON Job Logging             | This log is configured by Default                                                                  |
| Pods logs          | /var/log/pods/ * / * / * log                    | k8s pods                     | This log is configured by Default                                                                  |
| Access Logs        | /var/log/dirsrv/slapd-<Realm Name>/access | Directory Server Utilization | This log is available when FreeIPA or 389ds is set up ( ie when   enable_security_support is set to 'true') |
| Error Log          | /var/log/dirsrv/slapd-<Realm Name>/errors | Directory Server Errors      | This log is available when FreeIPA or 389ds is set up ( ie when   enable_security_support is set to 'true') |
| CA Transaction Log | /var/log/pki/pki-tomcat/ca/transactions   | FreeIPA PKI Transactions     | This log is available when FreeIPA or 389ds is set up ( ie when   enable_security_support is set to 'true') |
| KRB5KDC            | /var/log/krb5kdc.log                      | KDC Utilization              | This log is available when FreeIPA or 389ds is set up ( ie when   enable_security_support is set to 'true') |
| Secure logs        | /var/log/secure                           | Login Error Codes            | This log is available when FreeIPA or 389ds is set up ( ie when   enable_security_support is set to 'true') |
| HTTPD logs         | /var/log/httpd/*                          | FreeIPA API Call             | This log is available when FreeIPA or 389ds is set up ( ie when   enable_security_support is set to 'true') |
| DNF logs           | /var/log/dnf.log                          | Installation Logs            | This log is configured on Rocky OS                                                                 |
| Zypper Logs        | /var/log/zypper.log                       | Installation Logs            | This log is configured on Leap OS                                                                  |




