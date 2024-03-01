Centralized authentication on the cluster
==========================================

The security feature allows users to set up FreeIPA and LDAP to help authenticate into HPC clusters.

.. note:: 
    * Nodes provisioned using the Omnia provision tool do not require a RedHat subscription to run ``security.yml`` on RHEL target nodes.
    * For RHEL target nodes not provisioned by Omnia, ensure that RedHat subscription is enabled on all target nodes. Every target node will require a RedHat subscription.


Configuring FreeIPA/LDAP security
________________________________

**Pre requisites**

* Run ``local_repo.yml`` to create offline repositories of FreeIPA or OpenLDAP. If both were downloaded, ensure that the non-required system is removed from ``input/software_config.json`` before running ``security.yml``. For more information, `click here <../../InstallationGuides/LocalRepo/index.html>`_.

* Enter the following parameters in ``input/security_config.yml``.

.. csv-table:: Parameters for Authentication
   :file: ../../Tables/security_config.csv
   :header-rows: 1
   :keepspace:

.. csv-table:: Parameters for OpenLDAP configuration
   :file: ../../Tables/security_config_ldap.csv
   :header-rows: 1
   :keepspace:

.. csv-table:: Parameters for FreeIPA configuration
   :file: ../../Tables/security_config_freeipa.csv
   :header-rows: 1
   :keepspace:

.. [1] Boolean parameters do not need to be passed with double or single quotes.

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
3. To set up a password for this account, use the command ``ldappasswd -D <enter admin binddn > -w < bind_password > -S <user_dn>``. The value of ``user_dn`` is the distinguished name that indicates where the user was created. (In this example, ``ldapuser,ou=People,dc=omnia,dc=test``)



Configuring login node security
________________________________

**Prerequisites**

* Run ``local_repo.yml`` to create an offline repository of all utilities used to secure the login node. For more information, `click here. <../../InstallationGuides/LocalRepo/SecureLoginNode.html>`_

Enter the following parameters in ``input/login_node_security_config.yml``.

+--------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Variable                 | Details                                                                                                                                                                        |
+==========================+================================================================================================================================================================================+
| **max_failures**         | The number of login failures that can take place before the account is   locked out.                                                                                           |
|      ``integer``         |                                                                                                                                                                                |
|      Optional            |      **Default values**: ``3``                                                                                                                                                 |
+--------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|**failure_reset_interval**| Period (in seconds) after which the number of failed login attempts is   reset. Min value: 30; Max value: 60.                                                                  |
|      ``integer``         |                                                                                                                                                                                |
|      Optional            |      **Default values**: ``60``                                                                                                                                                |
+--------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| **lockout_duration**     | Period (in seconds) for which users are locked out. Min value: 5; Max   value: 10.                                                                                             |
|      ``integer``         |                                                                                                                                                                                |
|      Optional            |      **Default values**: ``10``                                                                                                                                                |
+--------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|**session_timeout**       | User sessions that have been idle for a specific period can be ended   automatically. Min value: 90; Max value: 180.                                                           |
|      ``integer``         |                                                                                                                                                                                |
|      Optional            |      **Default values**: ``180``                                                                                                                                               |
+--------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|**alert_email_address**   | Email address used for sending alerts in case of authentication failure.   When blank, authentication failure alerts are disabled. Currently, only one   email ID is accepted. |
|      ``string``          |                                                                                                                                                                                |
|      Optional            |                                                                                                                                                                                |
+--------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|**user**                  | Access control list of users. Accepted formats are username@ip   (root@1.2.3.4) or username (root). Multiple users can be separated using   whitespaces.                       |
|      ``string``          |                                                                                                                                                                                |
|      Optional            |                                                                                                                                                                                |
+--------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|**allow_deny**            | This variable decides whether users are to be allowed or denied access.   Ensure that AllowUsers or DenyUsers entries on sshd configuration file are   not commented.          |
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
|**restrict_softwares**    | List of services to be disabled (Comma-separated). Example:   'telnet,lpd,bluetooth'                                                                                           |
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

The inventory should contain auth_server as per the inventory file in `samplefiles <../../samplefiles.html#inventory-file>`_. The inventory file is case-sensitive. Follow the casing provided in the sample file link.

    * Do not include the IP of the control plane or local host in the auth_server group in the passed inventory.
    * To enable security features on the login node, ensure that ``enable_secure_login_node`` in ``input/security_config.yml`` is set to true.
    * To customize the security features on the login node, fill out the parameters in ``input/login_node_security_config.yml``.
    * If a subsequent run of ``security.yml`` fails, the ``security_config.yml`` file will be unencrypted.


.. caution:: No users will be created by Omnia.


.. toctree::
    ReplicatingLDAP
