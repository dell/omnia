LDAP authentication
======================

LDAP, the Lightweight Directory Access Protocol, is a mature, flexible, and well supported standards-based mechanism for interacting with directory servers.

Manager and compute nodes will have LDAP client installed and configured if ``ldap_required`` is set to true. The login node does not have LDAP client installed.

.. warning:: No users/groups will be created by Omnia.
