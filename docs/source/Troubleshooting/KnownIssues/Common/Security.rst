Centralized authentication
=============================

⦾ **What to do when** ``omnia.yml`` **fails while completing the security role, and returns the following error message:** ``Error: kinit: Connection refused while getting default cache`` **?**

**Resolution**:

1. Start the sssd-kcm.socket using the following command: ::
    
    systemctl start sssd-kcm.socket

2. Re-run the ``omnia.yml`` playbook.


⦾ **Why does the** ``TASK: Security: Authenticate as admin`` **fail?**

**Potential Cause**: The required services are not running on the node. Verify the service status using: ::

    systemctl status sssd-kcm.socket
    systemctl status sssd.service

**Resolution**:

1. Restart the services using:  ::

    systemctl start sssd-kcm.socket
    systemctl start sssd.service

2. Re-run ``omnia.yml`` using: ::

    ansible-playbook omnia.yml


⦾ **While trying to deploy OpenLDAP, why does** ``omnia.yml`` **execution fail during the** ``TASK [/opt/omnia/ldap/ansible-role-ldaptoolbox-openldap : load config from file]`` **?**

**Resolution**: To resolve this issue, deploy the authentication server (``auth_server``) on a dedicated node that is not part of any other cluster, such as a Kubernetes or Slurm cluster.

