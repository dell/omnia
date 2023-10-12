Centralized authentication on the cluster
==========================================

The security feature allows users to set up FreeIPA and LDAP to help authenticate into HPC clusters.

.. note:: 
    * Nodes provisioned using the Omnia provision tool do not require a RedHat subscription to run ``security.yml`` on RHEL target nodes.
    * For RHEL target nodes not provisioned by Omnia, ensure that RedHat subscription is enabled on all target nodes. Every target node will require a RedHat subscription.


Configuring FreeIPA/LDAP security
________________________________

Enter the following parameters in ``input/security_config.yml``.

+----------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Parameter                  | Details                                                                                                                                                                                                                                                         |
+============================+=================================================================================================================================================================================================================================================================+
| freeipa_required           | Boolean indicating whether FreeIPA is required or not.                                                                                                                                                                                                          |
|      ``boolean``           |                                                                                                                                                                                                                                                                 |
|      Optional              |      Choices:                                                                                                                                                                                                                                                   |
|                            |                                                                                                                                                                                                                                                                 |
|                            |      * ``true`` <- Default                                                                                                                                                                                                                                      |
|                            |      * ``false``                                                                                                                                                                                                                                                |
+----------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| realm_name                 | Sets the intended realm name.                                                                                                                                                                                                                                   |
|      ``string``            |                                                                                                                                                                                                                                                                 |
|      Optional              |      **Default values**: ``OMNIA.TEST``                                                                                                                                                                                                                         |
+----------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| directory_manager_password | Password authenticating admin level access to the Directory for system   management tasks. It will be added to the instance of directory server   created for IPA.Required Length: 8 characters. The password must not contain   -,, ‘,”                        |
|      ``string``            |                                                                                                                                                                                                                                                                 |
|      Optional              |                                                                                                                                                                                                                                                                 |
+----------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| kerberos_admin_password    | “admin” user password for the IPA server on RockyOS.                                                                                                                                                                                                            |
|      ``string``            |                                                                                                                                                                                                                                                                 |
|      Optional              |                                                                                                                                                                                                                                                                 |
+----------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ldap_required              | Boolean indicating whether ldap client is required or not.                                                                                                                                                                                                      |
|      ``boolean``           |                                                                                                                                                                                                                                                                 |
|      Optional              |      Choices:                                                                                                                                                                                                                                                   |
|                            |                                                                                                                                                                                                                                                                 |
|                            |      * ``false`` <- Default                                                                                                                                                                                                                                     |
|                            |      * ``true``                                                                                                                                                                                                                                                 |
+----------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| domain_name                | Sets the intended domain name.                                                                                                                                                                                                                                  |
|      ``string``            |                                                                                                                                                                                                                                                                 |
|      Optional              |      **Default values**: ``omnia.test``                                                                                                                                                                                                                         |
+----------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ldap_server_ip             | LDAP server IP. Required if ``ldap_required`` is true. There should be an   explicit LDAP server running on this IP.                                                                                                                                            |
|      ``string``            |                                                                                                                                                                                                                                                                 |
|      Optional              |                                                                                                                                                                                                                                                                 |
+----------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ldap_connection_type       | For a TLS connection, provide a valid certification path. For an SSL   connection, ensure port 636 is open.                                                                                                                                                     |
|      ``string``            |                                                                                                                                                                                                                                                                 |
|      Optional              |      **Default values**: ``TLS``                                                                                                                                                                                                                                |
+----------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ldap_ca_cert_path          | This variable accepts Server Certificate Path. Make sure certificate is   present in the path provided. The certificate should have .pem or .crt   extension. This variable is mandatory if connection type is TLS.                                             |
|      ``string``            |                                                                                                                                                                                                                                                                 |
|      Optional              |      **Default values**: ``/etc/openldap/certs/omnialdap.pem``                                                                                                                                                                                                  |
+----------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| user_home_dir              |  This variable accepts the user   home directory path for ldap configuration.    If nfs mount is created for user home, make sure you provide the LDAP   users mount home directory path.                                                                       |
|      ``string``            |                                                                                                                                                                                                                                                                 |
|      Optional              |      **Default values**: ``/home``                                                                                                                                                                                                                              |
+----------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ldap_bind_username         | If LDAP server is configured with bind dn then bind dn user to be   provided. If this value is not provided (when bind is configured in server)   then ldap authentication fails. Omnia does not validate this input. Ensure   that it is valid and proper.     |
|      ``string``            |                                                                                                                                                                                                                                                                 |
|      Optional              |      **Default values**: ``admin``                                                                                                                                                                                                                              |
+----------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ldap_bind_password         | If LDAP server is configured with bind dn then bind dn password to be   provided. If this value is not provided (when bind is configured in server)   then ldap authentication fails. Omnia does not validate this input. Ensure   that it is valid and proper. |
|      ``string``            |                                                                                                                                                                                                                                                                 |
|      Optional              |                                                                                                                                                                                                                                                                 |
+----------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| enable_secure_login_node   | Boolean value deciding whether security features are enabled on the Login   Node.                                                                                                                                                                               |
|      ``boolean``           |                                                                                                                                                                                                                                                                 |
|      Optional              |      Choices:                                                                                                                                                                                                                                                   |
|                            |                                                                                                                                                                                                                                                                 |
|                            |      * ``false`` <- Default                                                                                                                                                                                                                                     |
|                            |      * ``true``                                                                                                                                                                                                                                                 |
+----------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

.. note:: When ``ldap_required`` is true, ``freeipa_required`` has to be false. Conversely, when `freeipa_required`` is true, ``ldap_required`` has to be false.



Configuring login node security
________________________________

Enter the following parameters in ``input/login_node_security_config.yml``.

+--------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Variable                 | Details                                                                                                                                                                        |
+==========================+================================================================================================================================================================================+
| max_failures             | The number of login failures that can take place before the account is   locked out.                                                                                           |
|      ``integer``         |                                                                                                                                                                                |
|      Optional            |      **Default values**: ``3``                                                                                                                                                 |
+--------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| failure_reset_interval   | Period (in seconds) after which the number of failed login attempts is   reset. Min value: 30; Max value: 60.                                                                  |
|      ``integer``         |                                                                                                                                                                                |
|      Optional            |      **Default values**: ``60``                                                                                                                                                |
+--------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| lockout_duration         | Period (in seconds) for which users are locked out. Min value: 5; Max   value: 10.                                                                                             |
|      ``integer``         |                                                                                                                                                                                |
|      Optional            |      **Default values**: ``10``                                                                                                                                                |
+--------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| session_timeout          | User sessions that have been idle for a specific period can be ended   automatically. Min value: 90; Max value: 180.                                                           |
|      ``integer``         |                                                                                                                                                                                |
|      Optional            |      **Default values**: ``180``                                                                                                                                               |
+--------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| alert_email_address      | Email address used for sending alerts in case of authentication failure.   When blank, authentication failure alerts are disabled. Currently, only one   email ID is accepted. |
|      ``string``          |                                                                                                                                                                                |
|      Optional            |                                                                                                                                                                                |
+--------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| user                     | Access control list of users. Accepted formats are username@ip   (root@1.2.3.4) or username (root). Multiple users can be separated using   whitespaces.                       |
|      ``string``          |                                                                                                                                                                                |
|      Optional            |                                                                                                                                                                                |
+--------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| allow_deny               | This variable decides whether users are to be allowed or denied access.   Ensure that AllowUsers or DenyUsers entries on sshd configuration file are   not commented.          |
|      ``string``          |                                                                                                                                                                                |
|      Optional            |      Choices:                                                                                                                                                                  |
|                          |                                                                                                                                                                                |
|                          |      * ``allow`` <- Default                                                                                                                                                    |
|                          |      * ``deny``                                                                                                                                                                |
+--------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| restrict_program_support | This variable is used to disable services. Root access is   mandatory.                                                                                                         |
|      ``boolean``         |                                                                                                                                                                                |
|      Optional            |      Choices:                                                                                                                                                                  |
|                          |                                                                                                                                                                                |
|                          |      * ``false`` <- Default                                                                                                                                                    |
|                          |      * ``true``                                                                                                                                                                |
+--------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| restrict_softwares       | List of services to be disabled (Comma-separated). Example:   'telnet,lpd,bluetooth'                                                                                           |
|      ``string``          |                                                                                                                                                                                |
|      Optional            |      Choices:                                                                                                                                                                  |
|                          |                                                                                                                                                                                |
|                          |      * ``telnet``                                                                                                                                                              |
|                          |      * ``lpd``                                                                                                                                                                 |
|                          |      * ``bluetooth``                                                                                                                                                           |
|                          |      * ``rlogin``                                                                                                                                                              |
|                          |      * ``rexec``                                                                                                                                                               |
+--------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+


Installing LDAP Client
________________________

Manager and compute nodes will have LDAP client installed and configured if ``ldap_required`` is set to true. The login node does not have LDAP client installed.

.. caution:: No users/groups will be created by Omnia.

FreeIPA installation on the NFS node
-------------------------------------

IPA services are used to provide account management and centralized authentication.

To customize your installation of FreeIPA, enter the following parameters in ``input/security_config.yml``.

+-------------------------+-----------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------+
| Input Parameter         | Definition                                                      | Variable value                                                                                                                                        |
+=========================+=================================================================+=======================================================================================================================================================+
| kerberos_admin_password | "admin" user password for the IPA server on RockyOS and RedHat. | The password can be found in the file ``input/security_config.yml`` .                                                                                 |
+-------------------------+-----------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------+
| ipa_server_hostname     | The hostname of the IPA server                                  | The hostname can be found on the manager node.                                                                                                        |
+-------------------------+-----------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------+
| domain_name             | Domain name                                                     | The domain name can be found in the file ``input/security_config.yml``.                                                                               |
+-------------------------+-----------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------+
| ipa_server_ipadress     | The IP address of the IPA server                                | The IP address can be found on the IPA server on the manager node using the ``ip a`` command. This IP address should be accessible from the NFS node. |
+-------------------------+-----------------------------------------------------------------+-------------------------------------------------------------------------------------------------------------------------------------------------------+


To set up IPA services for the NFS node in the target cluster, run the following command from the ``utils/cluster`` folder on the control plane: ::

    cd utils/cluster
    ansible-playbook install_ipa_client.yml -i inventory -e kerberos_admin_password="" -e ipa_server_hostname="" -e domain_name="" -e ipa_server_ipadress=""


.. include:: ../../Appendices/hostnamereqs.rst

.. note:: Use the format specified under `NFS inventory in the Sample Files <../../samplefiles.html#nfs-server-inventory-file>`_ for inventory.

Running the security role
--------------------------

Run: ::

    cd security
    ansible-playbook security.yml -i inventory

The inventory should contain compute, manager, login as per the inventory file in `samplefiles <../../samplefiles.html#inventory-file>`_. The inventory file is case-sensitive. Follow the casing provided in the sample file link.

    * To enable security features on the login node, ensure that ``enable_secure_login_node`` in ``input/security_config.yml`` is set to true.
    * To customize the security features on the login node, fill out the parameters in ``input/login_node_security_config.yml``.
    * If a subsequent run of ``security.yml`` fails, the ``security_config.yml`` file will be unencrypted.


.. caution:: No users/groups will be created by Omnia.
