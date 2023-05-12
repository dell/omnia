Centralized authentication systems
===================================

To enable centralized authentication in the cluster, Omnia installs either:

 - FreeIPA
 - LDAP Client

.. note:: 
    * Nodes provisioned using the Omnia provision tool do not require a RedHat subscription to run ``security.yml`` on RHEL target nodes.
    * For RHEL target nodes not provisioned by Omnia, ensure that RedHat subscription is enabled on all target nodes. Every target node will require a RedHat subscription.



Using FreeIPA
--------------

Enter the following parameters in ``input/security_config.yml``.

+----------------------------+----------------------------------------------------------------------------------------------+
| Parameter                  | Details                                                                                      |
+============================+==============================================================================================+
| freeipa_required           | Boolean indicating whether FreeIPA is required or not.                                       |
|      ``boolean``           |                                                                                              |
|      Required              |      Choices:                                                                                |
|                            |                                                                                              |
|                            |      * ``true`` <- Default                                                                   |
|                            |                                                                                              |
|                            |      * ``false``                                                                             |
+----------------------------+----------------------------------------------------------------------------------------------+
| realm_name                 | Sets the intended realm name.                                                                |
|      ``string``            |                                                                                              |
|      Required              |      **Default value**: ``OMNIA.TEST``                                                       |
+----------------------------+----------------------------------------------------------------------------------------------+
| directory_manager_password | * Password authenticating admin level access to the Directory for system   management tasks. |
|      ``string``            |      * It will be added to the instance of directory server created for   IPA.               |
|      Required              |      * Required Length: 8 characters.                                                        |
|                            |      * The password must not contain -,, ‘,”                                                 |
+----------------------------+----------------------------------------------------------------------------------------------+
| kerberos_admin_password    | “admin”   user password for the IPA server on RockyOS.                                       |
|      ``string``            |                                                                                              |
|      Required              |                                                                                              |
+----------------------------+----------------------------------------------------------------------------------------------+
| domain_name                | Sets the intended domain   name                                                              |
|      ``string``            |                                                                                              |
|      Required              |      **Default value**: ``omnia.test``                                                       |
+----------------------------+----------------------------------------------------------------------------------------------+

.. note::

    The ``input/omnia_config.yml`` file is encrypted on the first run of the provision tool:
        To view the encrypted parameters: ::

            ansible-vault view security_config.yml --vault-password-file .security_vault_key

        To edit the encrypted parameters: ::

            ansible-vault edit security_config.yml --vault-password-file .security_vault_key



Omnia installs a FreeIPA server on the manager node and FreeIPA clients on the compute and login node using one of the below commands: ::

    ansible-playbook security.yml -i inventory

Where inventory follows the format defined under inventory file in the provided `Sample Files <../../samplefiles.html>`_ ::

    ansible-playbook omnia.yml -i inventory

Where inventory follows the format defined under inventory file in the provided `Sample Files <../../samplefiles.html>`_ The ``omnia.yml`` playbook installs Slurm, BeeFGS Client, NFS Client in addition to freeIPA.

.. note::

    * Omnia does not create any accounts (HPC users) on FreeIPA. To create a user, check out FreeIPA documentation.

    * Alternatively, use the below command with admin credentials: ::

    ipa user-add --homedir=<nfs_dir_path> --password


**Setting up Passwordless SSH for FreeIPA**

Once user accounts are created, admins can enable passwordless SSH for users to run HPC jobs.

To customize your setup of passwordless ssh, input parameters in ``input/passwordless_ssh_config.yml``

+-----------------------+--------------------------------------------------------------------------------------------------------------------+
| Parameter             | Details                                                                                                            |
+=======================+====================================================================================================================+
| user_name             | The user that requires passwordless SSH                                                                            |
|      ``string``       |                                                                                                                    |
|      Required         |                                                                                                                    |
+-----------------------+--------------------------------------------------------------------------------------------------------------------+
| authentication_type   | Indicates whether LDAP or FreeIPA is in use on the cluster.                                                        |
|      ``string``       |                                                                                                                    |
|      Required         |      Choices:                                                                                                      |
|                       |                                                                                                                    |
|                       |      * ``freeipa`` <- Default                                                                                      |
|                       |                                                                                                                    |
|                       |      * ``ldap``                                                                                                    |
+-----------------------+--------------------------------------------------------------------------------------------------------------------+
| freeipa_user_home_dir | * This variable accepts the user home directory path for freeipa   configuration.                                  |
|      ``string``       |      * If nfs mount is created for user home, make sure you provide the freeipa   users mount home directory path. |
|      Required         |                                                                                                                    |
|                       |      **Default value**: ``"/home"``                                                                                |
+-----------------------+--------------------------------------------------------------------------------------------------------------------+


Use the below command to enable passwordless SSH: ::

    ansible-playbook user_passwordless_ssh.yml -i inventory

Where inventory follows the format defined under inventory file in the provided `Sample Files <../../samplefiles.html>`_

.. caution:: Do not run ssh-keygen commands after passwordless SSH is set up on the nodes.


Using LDAP client
------------------

To add the cluster to an external LDAP server, Omnia enables the installation of LDAP client on the manager, compute and login nodes.

To customize your LDAP client installation, input parameters in ``input/security_config.yml``

+----------------------+----------------------------------------------------------------------------------------------------------------------+
| Parameter            | Details                                                                                                              |
+======================+======================================================================================================================+
| ldap_required        | Boolean indicating whether LDAP is required or not.                                                                  |
|      ``boolean``     |                                                                                                                      |
|      Required        |      Choices:                                                                                                        |
|                      |                                                                                                                      |
|                      |      * ``true`` <- Default                                                                                           |
|                      |                                                                                                                      |
|                      |      * ``false``                                                                                                     |
+----------------------+----------------------------------------------------------------------------------------------------------------------+
| domain_name          | Sets the intended domain name                                                                                        |
|      ``string``      |                                                                                                                      |
|      Required        |      **Default value**: ``omnia.test``                                                                               |
+----------------------+----------------------------------------------------------------------------------------------------------------------+
| ldap_server_ip       | LDAP server IP. Required if ``ldap_required`` is true. There should be an   explicit LDAP server running on this IP. |
|      ``string``      |                                                                                                                      |
|      Optional        |                                                                                                                      |
+----------------------+----------------------------------------------------------------------------------------------------------------------+
| ldap_connection_type | * For a TLS connection, provide a valid certification path.                                                          |
|      ``string``      | * For an SSL connection, ensure port 636 is open.                                                                    |
|      Required        |                                                                                                                      |
|                      |      Choices:                                                                                                        |
|                      |                                                                                                                      |
|                      |      * ``TLS`` <- Default                                                                                            |
|                      |                                                                                                                      |
|                      |      * ``SSL``                                                                                                       |
+----------------------+----------------------------------------------------------------------------------------------------------------------+
| ldap_ca_cert_path    | * This variable accepts Server Certificate Path.                                                                     |
|      ``string``      | * Make sure certificate is present in the path provided.                                                             |
|      Required        | * The certificate should have .pem or .crt extension.                                                                |
|                      | * This variable is mandatory if connection type is TLS.                                                              |
|                      |                                                                                                                      |
|                      |      **Default value**: ``/etc/openldap/certs/omnialdap.pem``                                                        |
+----------------------+----------------------------------------------------------------------------------------------------------------------+
| user_home_dir        | * This variable accepts the user home directory path for LDAP   configuration.                                       |
|      ``string``      | * If nfs mount is created for user home, make sure you provide the freeipa   users mount home directory path.        |
|      Required        |                                                                                                                      |
|                      |      **Default value**: ``"/home"``                                                                                  |
+----------------------+----------------------------------------------------------------------------------------------------------------------+
| ldap_bind_username   | * If LDAP server is configured with bind dn then bind dn user to be   provided.                                      |
|      ``string``      | * If this value is not provided (when bind is configured in server) then   ldap authentication fails.                |
|      Required        | * Omnia does not validate this input.                                                                                |
|                      | * Ensure that it is valid and proper.                                                                                |
|                      |                                                                                                                      |
|                      |      **Default value**: ``admin``                                                                                    |
+----------------------+----------------------------------------------------------------------------------------------------------------------+
| ldap_bind_password   | * If LDAP server is configured with bind dn then bind dn password to be   provided.                                  |
|      ``string``      | * If this value is not provided (when bind is configured in server) then   ldap authentication fails.                |
|      Required        | * Omnia does not validate this input.                                                                                |
|                      | * Ensure that it is valid and proper.                                                                                |
|                      |                                                                                                                      |
|                      |      **Default value**: ``admin``                                                                                    |
+----------------------+----------------------------------------------------------------------------------------------------------------------+

.. note:: Omnia does not create any accounts (HPC users) on LDAP. To create a user, check out `LDAP documentation. <https://docs.oracle.com/cd/E19857-01/820-7651/bhacc/index.html>`_


**Setting up Passwordless SSH for LDAP**

Once user accounts are created, admins can enable passwordless SSH for users to run HPC jobs.

.. note:: Ensure that the control plane can reach the designated LDAP server

To customize your setup of passwordless ssh, input parameters in ``input/passwordless_ssh_config.yml``

+--------------------------+-------------------------------------------------------------------------------------------------------+
| Parameter                | Details                                                                                               |
+==========================+=======================================================================================================+
| user_name                | The user that requires passwordless SSH                                                               |
|      ``string``          |                                                                                                       |
|      Required            |                                                                                                       |
+--------------------------+-------------------------------------------------------------------------------------------------------+
| authentication_type      | Indicates whether LDAP or FreeIPA is in use on the cluster.                                           |
|      ``string``          |                                                                                                       |
|      Required            |      Choices:                                                                                         |
|                          |                                                                                                       |
|                          |      * ``freeipa`` <- Default                                                                         |
|                          |                                                                                                       |
|                          |      * ``ldap``                                                                                       |
+--------------------------+-------------------------------------------------------------------------------------------------------+
| ldap_organizational_unit | * Distinguished name i.e dn in ldap is used to identify an entity in a   LDAP.                        |
|      ``string``          | * This variable includes the organizational unit (ou) which is used to   identifies user in the LDAP. |
|      Required            | * Only provide ou details i.e ou=people, as domain name and userid is   accepted already.             |
|                          | * By default ou=People                                                                                |
+--------------------------+-------------------------------------------------------------------------------------------------------+


Use the below command to enable passwordless SSH: ::

    ansible-playbook user_passwordless_ssh.yml -i inventory

Where inventory follows the format defined under inventory file. ::

    [manager]
    10.5.0.101

    [compute]
    10.5.0.102
    10.5.0.103

    [ldap_server]
    10.5.0.105


.. caution:: Do not run ssh-keygen commands after passwordless SSH is set up on the nodes.












