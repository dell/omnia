Securing the cluster
=====================

Enabling Security: Login Node
-----------------------------

* Verify that the login node host name has been set. If not, use the following steps to set it.

    * Set hostname of the login node to hostname.domainname format using the below command:

      ``hostnamectl set-hostname <hostname>.<domainname>``

    Eg: ``hostnamectl set-hostname login-node.omnia.test``

    * Add the set hostname in ``/etc/hosts`` using vi editor.



  ``vi /etc/hosts``



    * Add the IP of the login node with the above hostname using ``hostnamectl`` command in last line of the file.



  Eg:  xx.xx.xx.xx <hostname>



.. include:: ../../Appendices/hostnamereqs.rst


LDAP client support
------------------

* Ensure that an LDAP server is set up outside the cluster.

* Ensure that a Self Signed Certificate or a CA signed certificate is available for TLS encrypted connectivity.

* Ports 389 and 636 should be open on the server.

* Ensure that the LDAP server is reachable to the entire cluster.

* Ensure that firewall.d allows for ldapd communication.

FreeIPA
---------

FreeIPA will be installed when ``login_node_required`` is TRUE.

.. caution:: Since both FreeIPA and LDAP are authentication systems, only one of the two can be installed at any given time.

