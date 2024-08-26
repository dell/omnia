Centralized authentication
=============================

⦾ **Why am I unable to login using LDAP credentials after successfully creating a user account?**

**Potential Cause**: Whitespaces in the LDIF file may have caused an encryption error. Verify whether there are any whitespaces in the file by running ``cat -vet <filename>``.

**Resolution**: Remove the whitespaces and re-run the LDIF file.


⦾ **Why does the task: TASK [hostname_validation: Verify the domain name is not blank in hostname] fail?**

**Potential Cause**: Hostname is not configured properly with the domain name, on the target node.

**Resolution**: Use the following commands to configure the hostname properly: ::


        sysctl kernel.hostname=node001.omnia.test
        hostnamectl set-hostname node001.omnia.test


.. note:: ``node001.omnia.test`` is an acceptable sample hostname.


⦾ **Why does the user login fail for an OpenLDAP user?**

**Potential Cause**: Incorrect OpenLDAP service is running on the authentication server.

**Resolution**: Ensure that ``slapd-ltb.service`` is running on the authentication server. Use the following command to check if the service running: ::

    systemctl status slapd-ltb.service