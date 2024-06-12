How to replicate OpenLDAP server
---------------------------------
.. note:: This is a manual and optional configuration that the user can perform.

Once Omnia has set up an OpenLDAP server for the cluster, external LDAP servers can be replicated onto the cluster OpenLDAP server using the following steps.

**[Optional]Create a replication user**

1. Create an LDIF file (eg: ``replication_user.ldif``) on the external LDAP server (source) containing the following information:

    * DN: The distinguished name that indicates where the user will be created.
    * objectClass: The object class specifies the mandatory and optional attributes that can be associated with an entry of that class. Here, the values are ``simpleSecurityObject``, ``account``, and ``shadowAccount``.
    * UID: The username of the replication user.
    * Description: A user-defined string describing the account.
    * UserPassword: The SHA encrypted value of the intended user password. This can be obtained using ``slappasswd``

.. note:: In case of external LDAP server replication, ensure that the ``homeDirectory`` is always set to ``/home``.

Below is a sample file: ::

    dn: uid=replicauser,dc=orchid,dc=cluster
    objectClass: simpleSecurityObject
    objectclass: account
    objectClass: shadowAccount
    uid: replicauser
    description: Replication User
    userPassword: {SSHA}BL5xdrUvHQ8GPvdvHhO/4OmKHYoXQlIK

2. Run the command ``ldapadd -D <enter admin binddn > -w < bind_password > -f replication_user.ldif`` to execute the LDIF file and create the account.

**Initiate the replication**

1. Create an LDIF file (eg: ``Replication.ldif``) on the auth server on the cluster (destination) containing the following information:

    * Provider: The IP address of the source LDAP server. It is routed over the LDAP protocol and via port 389.
    * binddn: The distinguished name of the dedicated replication user or admin user being used to authenticate the replication.
    * credentials: The corresponding password of the user indicated in ``binddn``.
    * searchbase: The groups of users to be replicated.

Below is a sample file: ::

    dn: olcDatabase={1}mdb,cn=config
    changetype: modify
    add: olcSyncRepl
    olcSyncRepl: rid=001
      provider=ldap://xx.xx.xx.xx:389/
      bindmethod=simple
      binddn="uid=replicauser,dc=orchid,dc=cluster"
      credentials=sync1234
      searchbase="dc=orchid,dc=cluster"
      scope=sub
      schemachecking=on
      type=refreshAndPersist
      retry="30 5 300 3"
      interval=00:00:05:00

2. Run the command ``ldapadd -D cn=<config_username>,cn=config -w < config_password > -f Replication.ldif`` to execute the LDIF file and initiate the replication.