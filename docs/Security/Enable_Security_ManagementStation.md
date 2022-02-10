# Enabling Security on the Management Station and Login Node

Omnia uses FreeIPA to enable security features like authorisation and access control.

## Enabling Authentication on the Management Station:

Set the parameter 'enable_security_support' to true in `base_vars.yml`

## Prerequisites Before Enabling FreeIPA:
* Enter the relevant values in `security_vars.yml`:

| Parameter Name | Default Value | Additional Information                                                                                           |
|----------------|---------------|------------------------------------------------------------------------------------------------------------------|
| domain_name    | omnia.test    | The domain name should not contain an underscore ( _ )                                                           |
| realm_name     | omnia.test    | The realm name should follow the following rules per https://www.freeipa.org/page/Deployment_Recommendations <br> * The realm name must not conflict with any other existing Kerberos realm name (e.g. name used by Active Directory). <br> * The realm name should be upper-case (EXAMPLE.COM) version of primary DNS domain name (example.com).  |

* Enter the relevant values in `login_vars.yml`:

| Parameter Name             | Default Value | Additional Information                                                                           |
|----------------------------|---------------|--------------------------------------------------------------------------------------------------|
| directory_manager_password |               | Password of the Directory Manager with full access to the directory for system management tasks. |
| ipa_admin_password         |               | "admin" user password for the IPA server                                                         |


## Log Aggregation via Grafana

[Loki](https://grafana.com/docs/loki/latest/fundamentals/overview/) is a datastore used to efficiently hold log data for security purposes. Using the `promtail` agent, logs are collated and streamed via a HTTP API.

>> __Note:__ When `control_plane.yml` is run, Loki is automatically set up as a data source on the Grafana UI.



### Querying Loki 

Loki uses basic regex based syntax to filter for specific jobs, dates or timestamps.

* Select the Explore ![Explore Icon](Telemetry_Visualization/Images/ExploreIcon.PNG) tab to select control-plane-loki from the drop down.
* Using [LogQL queries](https://grafana.com/docs/loki/latest/logql/log_queries/), all logs in `/var/log` can be accessed using filters (Eg: `{job=”Omnia”}` )

## Viewing Logs on the Dashboard

All log files can be viewed via the Dashboard tab (![Dashboard Icon](Telemetry_Visualization/Images/DashBoardIcon.PNG)). The Default Dashboard displays `omnia.log` and `syslog`. Custom dashboards can be created per user requirements.

Below is a list of all logs available to Loki and can be accessed on the dashboard:

| Name               | Location                                  | Purpose                      | Additional Information                                                                             |
|--------------------|-------------------------------------------|------------------------------|----------------------------------------------------------------------------------------------------|
| Omnia Logs         | /var/log/omnia.log                        | Omnia Log                    | This log is configured by Default                                                                  |
| syslogs            | /var/log/messages                         | System Logging               | This log is configured by Default                                                                  |
| Audit Logs         | /var/log/audit/audit.log                  | All Login Attempts           | This log is configured by Default                                                                  |
| CRON logs          | /var/log/cron                             | CRON Job Logging             | This log is configured by Default                                                                  |
| Pods logs          | /var/log/pods/*/*/*log                    | k8s pods                     | This log is configured by Default                                                                  |
| Access Logs        | /var/log/dirsrv/slapd-<Realm Name>/access | Directory Server Utilization | This log is available when FreeIPA is set up ( ie when   enable_security_support is set to 'true') |
| Error Log          | /var/log/dirsrv/slapd-<Realm Name>/errors | Directory Server Errors      | This log is available when FreeIPA is set up ( ie when   enable_security_support is set to 'true') |
| CA Transaction Log | /var/log/pki/pki-tomcat/ca/transactions   | FreeIPA PKI Transactions     | This log is available when FreeIPA is set up ( ie when   enable_security_support is set to 'true') |
| KRB5KDC            | /var/log/krb5kdc.log                      | KDC Utilization              | This log is available when FreeIPA is set up ( ie when   enable_security_support is set to 'true') |
| Secure logs        | /var/log/secure                           | Login Error Codes            | This log is available when FreeIPA is set up ( ie when   enable_security_support is set to 'true') |
| HTTPD logs         | /var/log/httpd/*                          | FreeIPA API Call             | This log is available when FreeIPA is set up ( ie when   enable_security_support is set to 'true') |
| DNF logs           | /var/log/dnf.log                          | Installation Logs            | This log is configured on Rocky OS                                                                 |
| Zypper Logs        | /var/log/zypper.log                       | Installation Logs            | This log is configured on Leap OS                                                                  |







