============================
Troubleshooting guide
============================

Connecting to ``mysqldb`` container
===================================

    * Start a bash session within the mysqldb pod using the ``podman exec -it mysqldb bash`` command.
    * Connect to mysql using the ``mysql -u <mysqldb_username> -p`` command and provide password when prompted.
    * Connect to database using the ``USE idrac_telemetrydb`` command.


Checking and updating encrypted parameters
=============================================

1. Move to the filepath where the parameters are saved (as an example, we will be using ``omnia_config_credentials.yml``): ::

        cd /input

2. To view the encrypted parameters: ::

        ansible-vault view omnia_config_credentials.yml --vault-password-file .omnia_config_credentials_key


3. To edit the encrypted parameters: ::

        ansible-vault edit omnia_config_credentials.yml --vault-password-file .omnia_config_credentials_key


Checking podman container status from the OIM
===============================================
   
   * Use this command to get a list of all running podman conatiners: ``podman ps``
   * Check the status of any specific podman conatiner: ``podman ps -f name=<container_name>``


Troubleshooting task failures during ``omnia.yml`` playbook execution
========================================================================

If any task fails for a host listed in the inventory during the execution of the ``omnia.yml`` playbook, it can cause a cascading effect, resulting in the failure of subsequent tasks in the playbook.

**Resolution**: In such cases, you should begin troubleshooting from the initial point of failure — the first task that encountered an error.