Centralized authentication
=============================

⦾ **Why would FreeIPA server/client installation fail? (version 1.5 and below)**

**Potential Cause**: The hostnames of the auth server nodes are not configured in the correct format.

**Resolution**: If you have enabled the option to install the login node in the cluster, set the hostnames of the nodes in the format: *hostname.domainname*. For example, *authserver_node.omnia.test* is a valid hostname for the auth server node.

.. note:: To find the cause for the failure of the FreeIPA server and client installation, see *ipaserver-install.log* in the auth server.