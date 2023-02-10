Centralized authentication systems
===================================

To enable centralized authentication in the cluster, Omnia installs either:

 - FreeIPA
 - LDAP Client

Using FreeIPA
--------------

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

Omnia installs a FreeIPA server on the manager node and FreeIPA clients on the compute and login node using one of the below commands: ::

    ansible-playbook -i inventory security.yml

Where inventory follows the format defined under inventory file in the provided `Sample Files <../../samplefiles.html>`_ ::

    ansible-playbook -i inventory omnia.yml

Where inventory follows the format defined under inventory file in the provided `Sample Files <../../samplefiles.html>`_ The ``omnia.yml`` playbook installs Slurm, BeeFGS Client, NFS Client in addition to freeIPA.

.. note::

* Omnia does not create any accounts (HPC users) on FreeIPA. To create a user, check out FreeIPA documentation.

* Alternatively, use the below command with admin credentials: ::

    ipa user-add --homedir=<nfs_dir_path> --password


**Setting up Passwordless SSH for FreeIPA**

Once user accounts are created, admins can enable passwordless SSH for users to run HPC jobs.

To customize your setup of passwordless ssh, input parameters in ``input/passwordless_ssh_config.yml``

+-----------------------+--------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Parameter             | Default, Accepted values | Required? | Additional information                                                                                                                                                                               |
+=======================+==========================+===========+======================================================================================================================================================================================================+
| user_name             |                          | Required  | The user that requires passwordless SSH                                                                                                                                                              |
+-----------------------+--------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| authentication_type   | freeipa, ldap            | Required  | Indicates whether LDAP or FreeIPA is in use on the cluster                                                                                                                                           |
+-----------------------+--------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| freeipa_user_home_dir | "/home"                  | Required  | This variable accepts the user home     directory path for freeipa configuration.    If nfs mount is created for user home,   make sure you provide the freeipa     users mount home directory path. |
+-----------------------+--------------------------+-----------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

Use the below command to enable passwordless SSH: ::

    ansible-playbook -i inventory passwordless_ssh.yml

Where inventory follows the format defined under inventory file in the provided `Sample Files <../../samplefiles.html>`_



Using LDAP client
------------------

To add the cluster to an external LDAP server, Omnia enables the installation of LDAP client on the manager, compute and login nodes.

To customize your LDAP client installation, input parameters in ``input/security_config.yml``

+----------------------+-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Parameter Name       | Values                            | Additional Information                                                                                                                                                                                                                                          |
+======================+===================================+=================================================================================================================================================================================================================================================================+
| ldap_required        |  **false**, true                  |  Boolean indicating whether ldap client is   required or not                                                                                                                                                                                                    |
+----------------------+-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| domain_name          | omnia.test                        | Sets the intended domain name                                                                                                                                                                                                                                   |
+----------------------+-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ldap_server_ip       |                                   | LDAP server IP. Required if   ``ldap_required`` is true. There should be an explicit LDAP server running on   this IP.                                                                                                                                          |
+----------------------+-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ldap_connection_type | TLS                               | For a TLS connection, provide a valid   certification path. For an SSL connection, ensure port 636 is open.                                                                                                                                                     |
+----------------------+-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ldap_ca_cert_path    | /etc/openldap/certs/omnialdap.pem | This variable accepts Server   Certificate Path. Make sure certificate is present in the path provided. The   certificate should have .pem or .crt extension. This variable is mandatory if   connection type is TLS.                                           |
+----------------------+-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| user_home_dir        | /home                             |  This variable accepts the user home   directory path for ldap configuration.    If nfs mount is created for user home, make sure you provide the LDAP   users mount home directory path.                                                                       |
+----------------------+-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ldap_bind_username   | admin                             | If LDAP server is configured with bind   dn then bind dn user to be provided. If this value is not provided (when bind   is configured in server) then ldap authentication fails. Omnia does not   validate this input. Ensure that it is valid and proper.     |
+----------------------+-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ldap_bind_password   |                                   | If LDAP server is configured with bind   dn then bind dn password to be provided. If this value is not provided (when   bind is configured in server) then ldap authentication fails. Omnia does not   validate this input. Ensure that it is valid and proper. |
+----------------------+-----------------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+


.. note:: Omnia does not create any accounts (HPC users) on LDAP. To create a user, check out `LDAP documentation. <https://docs.oracle.com/cd/E19857-01/820-7651/bhacc/index.html>`_


**Setting up Passwordless SSH for LDAP**

To add the cluster to an external LDAP server, Omnia enables the installation of LDAP client on the manager, compute and login nodes.

To customize your LDAP client installation, input parameters in ``input/security_config.yml``.

+--------------------------+--------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Parameter                | Default, Accepted values | Additional information                                                                                                                                                                                                                                                                        |
+==========================+==========================+===============================================================================================================================================================================================================================================================================================+
| user_name                |                          | The user that requires passwordless SSH                                                                                                                                                                                                                                                       |
+--------------------------+--------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| authentication_type      | freeipa, ldap            | Indicates whether LDAP or FreeIPA is in use on the cluster                                                                                                                                                                                                                                    |
+--------------------------+--------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ldap_organizational_unit |                          | Distinguished name i.e dn in ldap is used to identify an entity in a   LDAP. This variable includes the organizational unit (ou) which is used to   identifies user in the LDAP. Only provide ou details i.e ou=people, as domain   name and userid is accepted already. By default ou=People |
+--------------------------+--------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+


Use the below command to enable passwordless SSH: ::

    ansible-playbook -i inventory passwordless_ssh.yml

Where inventory follows the format defined under inventory file in the provided `Sample Files <../../samplefiles.html>`_














