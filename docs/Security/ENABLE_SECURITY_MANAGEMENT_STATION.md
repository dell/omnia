# Enabling Security on the Management Station

Omnia uses [FreeIPA (on RockyOS)](https://www.freeipa.org/page/Documentation
) and [389ds(on Leap)](https://doc.opensuse.org/documentation/leap/security/html/book-security/cha-security-ldap.html
) to enable security features like authorisation and access control.

>> __Note:__ For 389ds/SSSD to work, an external LDAP server has to be set up in your environment as Omnia does not configure LDAP.

## Enabling Authentication on the Management Station:

Set the parameter 'enable_security_support' to true in `base_vars.yml`

## Prerequisites Before Enabling Security:

* Set hostname of management station to hostname.domainname format using the below command:
`hostnamectl set-hostname <hostname>.<domainname>`
>>Eg: `hostnamectl set-hostname valdiationms.omnia.test`
>> __Note:__ 
>>	* The Hostname should not contain the following characters: , (comma), \. (period) or _ (underscore). However, the **domain name** is allowed commas and periods. 
>>	* The Hostname cannot start or end with a hyphen (-).
>>	* No upper case characters are allowed in the hostname.
>>	* The hostname cannot start with a number.

* Add the set hostname in `/etc/hosts` using vi editor.

`vi /etc/hosts`

* Add the IP of the management station with the above hostname using `hostnamectl` command in the last line of the file.
>> Eg: xx.xx.xx.xx <hostname>

* Enter the relevant values in `login_vars.yml`:

| Parameter Name             | Default Value | Additional Information                                                                           |
|----------------------------|---------------|--------------------------------------------------------------------------------------------------|
| ms_directory_manager_password |               | Password of the Directory Manager with full access to the directory for system management tasks. |
| ms_kerberos_admin_password         |               | "admin" user password for the IPA server on RockyOS. If LeapOS is in use, it is used as the "kerberos admin" user password for 389-ds                                                       |



* Enter the relevant values in `security_vars.yml`:

|  Variables    						                                               |  **Default**,   Accepted values                       |  Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
|--------------------------------------------------------------------------------------|-------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| domain_name                                                                          | **omnia.test**                                        | The domain name should not contain   an underscore ( _ )                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| realm_name                                                                           | **OMNIA.TEST**                                        | The realm name should follow the   following rules per   https://www.freeipa.org/page/Deployment_Recommendations   <br> * The realm name must not   conflict with any other existing     Kerberos realm name (e.g. name used by Active Directory). <br> *   The   realm name should be upper-case   (EXAMPLE.COM) version of primary DNS domain name (example.com).                                                                                                                                                                                                                                                                                                                                                |
| max_failures                                                                         | **3**                                                 | Failures allowed before lockout.   <br> This value cannot currently     be changed.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| failure_reset_interval                                                               | **60**                                                | Period (in seconds) after which the   number of failed login attempts is     reset <br> Accepted Values: 30-60                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| lockout_duration                                                                     | **10**                                                | Period (in seconds) for which users are   locked out. <br> Accepted     Values: 5-10                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| session_timeout                                                                      | **180**                                               | Period (in seconds) after which idle   users get logged out automatically     <br> Accepted Values: 30-90                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| alert_email_address                                                                  |                                                       | Email address used for sending alerts in   case of authentication failure. Currently, only one email address is   supported in this field.   <br>   If this variable is left blank, authentication failure alerts will   be disabled.                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| user                                                                                 |                                                       | Array of users that are allowed or   denied based on the `allow_deny`     value. Multiple users must be separated by a space. Accepted user value formats are: root root@xx.xx.xx.xx. <br> __Note:__ If IPs are to be specified in the user value, ensure that every IP associated with the host (often 2 or more, depending on how many NICs are on the host) in question is listed in the user list. <br> __Eg:__ For a host with IPs xx.xx.xx.xx and yy.yy.yy.yy where root is to be restricted, the user array will contain root@xx.xx.xx.xx root@yy.yy.yy.yy                                                                                                                                                                                             |                                                                                                                                                                                                                                                                                                        |
| allow_deny                                                                           | **Allow**                                             | This variable sets whether the user list   is Allowed or Denied. <br>     Accepted Values: Allow, Deny                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| restrict_program_support                                                             | **false**                                             | This variable sets whether the network   services/protocols listed in `restrict_softwares` are to be blocked.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| restrict_softwares                                                                   |                                                       | Array of services/protocols to be   blocked by Omnia. Values are to be separated by commas. <br> Accepted   values: telnet,lpd,bluetooth,rlogin,rexec <br> Non Accepted values:   ftp,smbd,nmbd,automount,portmap                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |

>> __Note:__ In the event that `control_plane.yml` fails after executing the control plane security tasks, `sshd` services will have to be restarted manually by the User.

## Limiting User Authentication over sshd

Users logging into this host can be __optionally__ allowed or denied using an access control list. All users to be allowed or denied are to be listed in the variable `user` in `security_vars.yml`. 

>> __Note:__ All users on the server will have to be defined manually. Omnia does not create any users by default.

## Session Timeout

To encourage security, users who have been idle over 3 minutes will be logged out automatically. To adjust this value, update the `session_timeout` variable in `security_vars.yml`. This variable is mandatory. 

## Restricting Program Support

Optionally, different communication protocols can be disabled on the management station using the `restrict_program_support` and `restrict_softwares` variables. These protocols include: telnet,lpd,bluetooth,rlogin and rexec. Features that cannot be disabled include: ftp,smbd,nmbd,automount and portmap. 

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
* Using [LogQL queries](https://grafana.com/docs/loki/latest/logql/log_queries/), all logs in `/var/log` can be accessed using filters (Eg: `{job=”Omnia”}` )

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







