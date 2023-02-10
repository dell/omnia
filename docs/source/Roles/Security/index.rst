Security
=========

The security role allows users to set up FreeIPA and LDAP to help authenticate into HPC clusters.

Configuring FreeIPA/LDAP security
________________________________

Enter the following parameters in ``input/security_config.yml``.

+----------------------------+-----------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Parameter Name             | Values                            | Additional Information                                                                                                                                                                                                                   |
+============================+===================================+==========================================================================================================================================================================================================================================+
| freeipa_required           | **true**, false                   | Boolean indicating whether FreeIPA is required or not.                                                                                                                                                                                   |
+----------------------------+-----------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| realm_name                 | OMNIA.TEST                        | Sets the intended realm name                                                                                                                                                                                                             |
+----------------------------+-----------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| directory_manager_password |                                   | Password authenticating admin level   access to the Directory for system management tasks. It will be added to the   instance of directory server created for IPA.Required Length: 8 characters.   The password must not contain -,, ‘,” |
+----------------------------+-----------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| kerberos_admin_password    |                                   | “admin” user password for the IPA   server on RockyOS.                                                                                                                                                                                   |
+----------------------------+-----------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| domain_name                | omnia.test                        | Sets the intended domain name                                                                                                                                                                                                            |
+----------------------------+-----------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ldap_required              |  **false**, true                  |  Boolean indicating whether ldap client is   required or not                                                                                                                                                                             |
+----------------------------+-----------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ldap_server_ip             |                                   | LDAP server IP. Required if   ``ldap_required`` is true.                                                                                                                                                                                 |
+----------------------------+-----------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ldap_connection_type       | TLS                               | For a TLS connection, provide a valid   certification path. For an SSL connection, ensure port 636 is open.                                                                                                                              |
+----------------------------+-----------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ldap_ca_cert_path          | /etc/openldap/certs/omnialdap.pem | This variable accepts Server   Certificate Path. Make sure certificate is present in the path provided. The   certificate should have .pem or .crt extension. This variable is mandatory if   connection type is TLS.                    |
+----------------------------+-----------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| user_home_dir              | /home                             |  This variable accepts the user home   directory path for ldap configuration.    If nfs mount is created for user home, make sure you provide the LDAP   users mount home directory path.                                                |
+----------------------------+-----------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ldap_bind_username         | admin                             | If LDAP server is configured with bind   dn then bind dn user to be provided. If this value is not provided (when bind   is configured in server) then ldap authentication fails.                                                        |
+----------------------------+-----------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ldap_bind_password         |                                   | If LDAP server is configured with bind   dn then bind dn password to be provided. If this value is not provided (when   bind is configured in server) then ldap authentication fails.                                                    |
+----------------------------+-----------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| enable_secure_login_node   | **false**, true                   | Boolean value deciding whether   security features are enabled on the Login Node.                                                                                                                                                        |
+----------------------------+-----------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

.. note:: When ``ldap_required`` is true, ``freeipa_required`` has to be false. Conversely, when `freeipa_required`` is true, ``ldap_required`` has to be false.



Configuring login node security
________________________________

Enter the following parameters in ``input/login_node_security_config.yml``.

+--------------------------+-----------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Variable                 | Default, Choices                  | Description                                                                                                                                                                    |
+==========================+===================================+================================================================================================================================================================================+
| max_failures             | **3**                             | The number of login failures that can take place before the account is   locked out.                                                                                           |
+--------------------------+-----------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| failure_reset_interval   | **60**                            | Period (in seconds) after which the number of failed login attempts is   reset. Min value: 30; Max value: 60.                                                                  |
+--------------------------+-----------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| lockout_duration         | **10**                            | Period (in seconds) for which users are locked out. Min value: 5; Max   value: 10.                                                                                             |
+--------------------------+-----------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| session_timeout          | **180**                           | User sessions that have been idle for a specific period can be ended   automatically. Min value: 90; Max value: 180.                                                           |
+--------------------------+-----------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| alert_email_address      |                                   | Email address used for sending alerts in case of authentication failure.   When blank, authentication failure alerts are disabled. Currently, only one   email ID is accepted. |
+--------------------------+-----------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| user                     |                                   | Access   control list of users. Accepted formats are username@ip (root@1.2.3.4) or   username (root). Multiple users can be separated using whitespaces.                       |
+--------------------------+-----------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| allow_deny               | **allow**, deny                   | This variable decides whether users are to be allowed or denied access.   Ensure that AllowUsers or DenyUsers entries on sshd configuration file are   not commented.          |
+--------------------------+-----------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| restrict_program_support | **false**, true                   | This   variable is used to disable services. Root access is mandatory.                                                                                                         |
+--------------------------+-----------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| restrict_softwares       | telnet,lpd,bluetooth,rlogin,rexec | List of services to be disabled (Comma-separated). Example:   'telnet,lpd,bluetooth'                                                                                           |
+--------------------------+-----------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

Installing LDAP Client
________________________

Manager and compute nodes will have LDAP client installed and configured if ``ldap_required`` is set to true. The login node does not have LDAP client installed.

.. warning:: No users/groups will be created by Omnia.

.. include:: ../Utils/freeipa_installation.rst

**Running the security role**

Run: ::

    cd security
    ansible-playbook security.yml -i inventory

The inventory should contain compute, manager, login_node as per the inventory file in `samplefiles <../../samplefiles.html#inventory-file>`_.

    * To enable security features on the login node, ensure that ``enable_secure_login_node`` in ``input/security_config.yml`` is set to true.
    * To customize the security features on the login node, fill out the parameters in ``input/login_node_security_config.yml``.

.. warning:: No users/groups will be created by Omnia.
