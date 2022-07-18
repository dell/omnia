# Logs Used for Troubleshooting

## 1. /var/log (Control Plane)

All log files can be viewed via the Dashboard tab (![Dashboard Icon](../Telemetry_Visualization/Images/DashBoardIcon.PNG)). The Default Dashboard displays `omnia.log` and `syslog`. Custom dashboards can be created per user requirements.

Below is a list of all logs available to Loki and can be accessed on the dashboard:

| Name               | Location                                  | Purpose                      | Additional Information                                                                             |
|--------------------|-------------------------------------------|------------------------------|----------------------------------------------------------------------------------------------------|
| Omnia Logs         | /var/log/omnia.log                        | Omnia Log                    | This log is configured by Default. This log can be used to track all changes made by all playbooks in the `omnia` directory.                                                                 |
| Omnia Control Plane| /var/log/omnia_control_plane.log          | Control plane Log            | This log is configured by Default. This log can be used to track all changes made by all playbooks in the `omnia/control_plane` directory.                                                            |
| Omnia Telemetry    | /var/log/omnia/omnia_telemetry.log        | Telemetry Log                | This log is configured by Default. This log can be used to track all changes made by all playbooks in the `omnia/telemetry` directory.                                                           |
| Omnia Tools        | /var/log/omnia/omnia_tools.log            | Tools Log                    | This log is configured by Default. This log can be used to track all changes made by all playbooks in the `omnia/tools` directory.                                                           |
| Omnia Platforms    | /var/log/omnia/omnia_platforms.log        | Platforms Log                | This log is configured by Default. This log can be used to track all changes made by all playbooks in the `omnia/platforms` directory.                                                           |
| Omnia Control Plane Tools| /var/log/omnia/omnia_control_plane_tools.log        | Control Plane tools logs                | This log is configured by Default. This log can be used to track all changes made by all playbooks in the `omnia/control_plane/tools` directory.                                                           |
| Node Info CLI log  | /var/log/omnia/collect_node_info/collect_node_info_yyyy-mm-dd-HHMMSS.log        | CLI Log                | This log is configured when AWX is disabled. This log can be used to track scheduled and unscheduled node inventory jobs initiated by CLI.                                                           |
| Device Info CLI log| /var/log/omnia/collect_device_info/collect_device_info_yyyy-mm-dd-HHMMSS.log        | CLI Log                | This log is configured when AWX is disabled. This log can be used to track scheduled and unscheduled device inventory jobs initiated by CLI.                                                           |
| iDRAC CLI log     | /var/log/omnia/idrac/idrac-yyyy-mm-dd-HHMMSS.log        | CLI Log                | This log is configured when AWX is disabled. This log can be used to track iDRAC jobs initiated by CLI.                                                           |
| Infiniband CLI log| //var/log/omnia/infiniband/infiniband-yyyy-mm-dd-HHMMSS.log        | CLI Log                | This log is configured when AWX is disabled. This log can be used to track Infiniband jobs initiated by CLI.                                                           |
| Ethernet CLI log| /var/log/omnia/ethernet/ethernet-yyyy-mm-dd-HHMMSS.log        | CLI Log                | This log is configured when AWX is disabled. This log can be used to track Ethernet jobs initiated by CLI.                                                           |
| Powervault CLI log| /var/log/omnia/powervault/powervault-yyyy-mm-dd-HHMMSS.log        | CLI Log                | This log is configured when AWX is disabled. This log can be used to track Powervault jobs initiated by CLI.                                                           |
| syslogs            | /var/log/messages                         | System Logging               | This log is configured by Default                                                                  |
| Audit Logs         | /var/log/audit/audit.log                  | All Login Attempts           | This log is configured by Default                                                                  |
| CRON logs          | /var/log/cron                             | CRON Job Logging             | This log is configured by Default                                                                  |
| Pods logs          | /var/log/pods/ * / * / * log              | k8s pods                     | This log is configured by Default                                                                  |
| Access Logs        | /var/log/dirsrv/slapd-<Realm Name>/access | Directory Server Utilization | This log is available when FreeIPA or 389ds is set up ( ie when   enable_security_support is set to 'true') |
| Error Log          | /var/log/dirsrv/slapd-<Realm Name>/errors | Directory Server Errors      | This log is available when FreeIPA or 389ds is set up ( ie when   enable_security_support is set to 'true') |
| CA Transaction Log | /var/log/pki/pki-tomcat/ca/transactions   | FreeIPA PKI Transactions     | This log is available when FreeIPA or 389ds is set up ( ie when   enable_security_support is set to 'true') |
| KRB5KDC            | /var/log/krb5kdc.log                      | KDC Utilization              | This log is available when FreeIPA or 389ds is set up ( ie when   enable_security_support is set to 'true') |
| Secure logs        | /var/log/secure                           | Login Error Codes            | This log is available when FreeIPA or 389ds is set up ( ie when   enable_security_support is set to 'true') |
| HTTPD logs         | /var/log/httpd/ *                         | FreeIPA API Calls            | This log is available when FreeIPA or 389ds is set up ( ie when   enable_security_support is set to 'true') |
| DNF logs           | /var/log/dnf.log                          | Installation Logs            | This log is configured on Rocky OS                                                                 |
| Zypper Logs        | /var/log/zypper.log                       | Installation Logs            | This log is configured on Leap OS                                                                  |
| BeeGFS Logs        | /var/log/beegfs-client.log                | BeeGFS Logs                  | This log is configured on BeeGFS client nodes.                                                                  |



## 2. Checking logs of individual containers:
   1. A list of namespaces and their corresponding pods can be obtained using:
      `kubectl get pods -A`
   2. Get a list of containers for the pod in question using:
      `kubectl get pods <pod_name> -o jsonpath='{.spec.containers[*].name}'`
   3. Once you have the namespace, pod and container names, run the below command to get the required logs:
      `kubectl logs pod <pod_name> -n <namespace> -c <container_name>`


## 3. Connecting to internal databases:
* TimescaleDB
	* Go inside the pod: `kubectl exec -it pod/timescaledb-0 -n telemetry-and-visualizations -- /bin/bash`
	* Connect to psql: `psql -U <postgres_username>`
	* Connect to database: `\c  < timescaledb_name >`
* MySQL DB
	* Go inside the pod: `kubectl exec -it pod/mysqldb-0  -n telemetry-and-visualizations -- /bin/bash`
	* Connect to psql: `psql -U <mysqldb_username> -p <mysqldb_password>`
	* Connect to database: `USE <mysqldb_name>`

## 4. Checking and updating encrypted parameters:
   1. Move to the filepath where the parameters are saved (as an example, we will be using `login_vars.yml`):
      `cd control_plane/input_params`
   2. To view the encrypted parameters:
   `ansible-vault view login_vars.yml --vault-password-file .login_vault_key`
   3. To edit the encrypted parameters:
    `ansible-vault edit login_vars.yml --vault-password-file .login_vault_key`
## 5. Checking pod status on the control plane
   * Select the pod you need to troubleshoot from the output of `kubectl get pods -A`
   * Check the status of the pod by running `kubectl describe pod <pod name> -n <namespace name>`

## 6. Omnia version file
The Omnia version number is stored in `/opt/omnia/omnia_version` when `control_plane.yml` is run.





