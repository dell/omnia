Centralized authentication on the cluster
==========================================

The security feature allows cluster admin users to set up FreeIPA or OpenLDAP in order to allow or deny user access.

.. note:: FreeIPA configuration is not supported on Ubuntu (only supported on RHEL/Rocky Linux).

Configuring OpenLDAP security
_______________________________

**Pre requisites**

* Run ``local_repo.yml`` to create offline repositories of FreeIPA or OpenLDAP. If both were downloaded, ensure that the non-required system is removed from ``input/software_config.json`` before running ``security.yml``. For more information, `click here <../../InstallationGuides/LocalRepo/index.html>`_.

* Enter the following parameters in ``input/security_config.yml``.

.. csv-table:: Parameters for Authentication
   :file: ../../../Tables/security_config.csv
   :header-rows: 1
   :keepspace:

.. csv-table:: Parameters for OpenLDAP configuration
   :file: ../../../Tables/security_config_ldap.csv
   :header-rows: 1
   :keepspace:

Running the security role
--------------------------

The wrapper playbook ``omnia.yml`` handles execution of the security or authentication role. Alternatively, execute the ``security.yml`` playbook: ::

    cd security
    ansible-playbook security.yml -i inventory

The inventory should contain auth_server as per the inventory file in `samplefiles <../../samplefiles.html#inventory-file>`_. The inventory file is case-sensitive. Follow the format provided in the sample file link.

    * Do not include the IP of the control plane or local host as the ``auth_server group`` in the inventory file.
    * To customize the security features on the login node, update the desired parameters in ``input/login_node_security_config.yml``.
    * If a subsequent run of ``security.yml`` fails, the ``security_config.yml`` file will be unencrypted.

.. note:: Installation of OpenLDAP server on the control plane is not supported.

.. caution:: No users will be created by Omnia.

Create a new user on OpenLDAP
-----------------------------

1. Create an LDIF file (eg: ``create_user.ldif``) on the auth server containing the following information:

    * DN: The distinguished name that indicates where the user will be created.
    * objectClass: The object class specifies the mandatory and optional attributes that can be associated with an entry of that class. Here, the values are ``inetOrgPerson``, ``posixAccount``, and ``shadowAccount``.
    * UID: The username of the replication user.
    * sn: The surname of the intended user.
    * cn: The given name of the intended user.

Below is a sample file: ::

    # User Creation
    dn: uid=ldapuser,ou=People,dc=omnia,dc=test
    objectClass: inetOrgPerson
    objectClass: posixAccount
    objectClass: shadowAccount
    cn: ldapuser
    sn: ldapuser
    loginShell:/bin/bash
    uidNumber: 2000
    gidNumber: 2000
    homeDirectory: /home/ldapuser
    shadowLastChange: 0
    shadowMax: 0
    shadowWarning: 0

    # Group Creation
    dn: cn=ldapuser,ou=Group,dc=omnia,dc=test
    objectClass: posixGroup
    cn: ldapuser
    gidNumber: 2000
    memberUid: ldapuser

.. note:: Avoid whitespaces when using an LDIF file for user creation. Extra spaces in the input data may be encrypted by OpenLDAP and cause access failures.

2. Run the command ``ldapadd -D <enter admin binddn > -w < bind_password > -f create_user.ldif`` to execute the LDIF file and create the account.
3. To set up a password for this account, use the command ``ldappasswd -D <enter admin binddn > -w < bind_password > -S <user_dn>``. The value of ``user_dn`` is the distinguished name that indicates where the user was created. (In this example, ``uid=ldapuser,ou=People,dc=omnia,dc=test``)

Setting up Passwordless SSH for the OpenLDAP users
-----------------------------------------------------------

Once user accounts are created, admins can enable password-less SSH for users to run HPC jobs on the cluster nodes.

.. note:: Once user accounts are created on the auth server, use the accounts to login to the cluster nodes to reset the password and create a corresponding home directory.

To customize your setup of password-less SSH, input custom parameters in ``input/passwordless_ssh_config.yml``.

+-----------------------+--------------------------------------------------------------------------------------------------------------------+
| Parameter             | Details                                                                                                            |
+=======================+====================================================================================================================+
| user_name             | The list of users that requires password-less SSH. Separate the list of users using a comma.                       |
|      ``string``       |  Eg: ``user1,user2,user3``                                                                                         |
|      Required         |                                                                                                                    |
+-----------------------+--------------------------------------------------------------------------------------------------------------------+
| authentication_type   | Indicates whether LDAP or FreeIPA is in use on the cluster.                                                        |
|      ``string``       |                                                                                                                    |
|      Required         |      Choices:                                                                                                      |
|                       |                                                                                                                    |
|                       |      ``ldap``   <- Default                                                                                         |
+-----------------------+--------------------------------------------------------------------------------------------------------------------+


Use the below command to enable password-less SSH: ::

    ansible-playbook user_passwordless_ssh.yml -i inventory

Where inventory follows the format defined under inventory file in the provided `Sample Files. <../../sample files.html>`_ The inventory file is case-sensitive. Follow the format provided in the sample file link.

.. caution:: Do not run SSH-keygen commands after password-less SSH is set up on the nodes.

Configuring login node security
________________________________

**Prerequisites**

* Run ``local_repo.yml`` to create an offline repository of all utilities used to secure the login node. For more information, `click here. <../../InstallationGuides/LocalRepo/index.html>`_

Enter the following parameters in ``input/login_node_security_config.yml``.

+-----------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Variable                    | Details                                                                                                                                                                        |
+=============================+================================================================================================================================================================================+
| **max_failures**            | The number of login failures that can take place before the account is   locked out.                                                                                           |
|      ``integer``            |                                                                                                                                                                                |
|      Optional               |      **Default values**: ``3``                                                                                                                                                 |
+-----------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|**failure_reset_interval**   | Period (in seconds) after which the number of failed login attempts is   reset. Min value: 30; Max value: 60.                                                                  |
|      ``integer``            |                                                                                                                                                                                |
|      Optional               |      **Default values**: ``60``                                                                                                                                                |
+-----------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| **lockout_duration**        | Period (in seconds) for which users are locked out. Min value: 5; Max   value: 10.                                                                                             |
|      ``integer``            |                                                                                                                                                                                |
|      Optional               |      **Default values**: ``10``                                                                                                                                                |
+-----------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|**session_timeout**          | User sessions that have been idle for a specific period can be ended   automatically. Min value: 90; Max value: 180.                                                           |
|      ``integer``            |                                                                                                                                                                                |
|      Optional               |      **Default values**: ``180``                                                                                                                                               |
+-----------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|**alert_email_address**      | Email address used for sending alerts in case of authentication failure.   When blank, authentication failure alerts are disabled. Currently, only one   email ID is accepted. |
|      ``string``             |                                                                                                                                                                                |
|      Optional               |                                                                                                                                                                                |
+-----------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|**user**                     | Access control list of users. Accepted formats are username@ip   (root@1.2.3.4) or username (root). Multiple users can be separated using   whitespaces.                       |
|      ``string``             |                                                                                                                                                                                |
|      Optional               |                                                                                                                                                                                |
+-----------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|**allow_deny**               | This variable decides whether users are to be allowed or denied access.   Ensure that AllowUsers or DenyUsers entries on sshd configuration file are   not commented.          |
|      ``string``             |                                                                                                                                                                                |
|      Optional               |      Choices:                                                                                                                                                                  |
|                             |                                                                                                                                                                                |
|                             |      * ``allow`` <- Default                                                                                                                                                    |
|                             |      * ``deny``                                                                                                                                                                |
+-----------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|**restrict_program_support** | This variable is used to disable services. Root access is   mandatory.                                                                                                         |
|      ``boolean``            |                                                                                                                                                                                |
|      Optional               |      Choices:                                                                                                                                                                  |
|                             |                                                                                                                                                                                |
|                             |      * ``false`` <- Default                                                                                                                                                    |
|                             |      * ``true``                                                                                                                                                                |
+-----------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|**restrict_softwares**       | List of services to be disabled (Comma-separated). Example:   'telnet,lpd,bluetooth'                                                                                           |
|      ``string``             |                                                                                                                                                                                |
|      Optional               |      Choices:                                                                                                                                                                  |
|                             |                                                                                                                                                                                |
|                             |      * ``telnet``                                                                                                                                                              |
|                             |      * ``lpd``                                                                                                                                                                 |
|                             |      * ``bluetooth``                                                                                                                                                           |
|                             |      * ``rlogin``                                                                                                                                                              |
|                             |      * ``rexec``                                                                                                                                                               |
+-----------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

Advanced Settings
------------------

* To install FreeIPA server on the NFS node, `click here <../../Roles/Utils/freeipa_installation.html>`_.

* To replicate the OpenLDAP server `click here <ReplicatingLDAP.html>`_.

* To set up the internal OpenLDAP server as a proxy, `click here <OpenLDAP_proxy.html>`_.