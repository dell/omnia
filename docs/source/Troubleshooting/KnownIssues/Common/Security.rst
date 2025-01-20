Centralized authentication
=============================

⦾ **What to do when** ``omnia.yml`` **fails while completing the security role, and returns the following error message: 'Error: kinit: Connection refused while getting default cache'?**

**Resolution**:

1. Start the sssd-kcm.socket: ``systemctl start sssd-kcm.socket``

2. Re-run ``omnia.yml``


⦾ **Why does the task 'security: Authenticate as admin' fail?**

**Potential Cause**: The required services are not running on the node. Verify the service status using: ::

    systemctl status sssd-kcm.socket
    systemctl status sssd.service

**Resolution**:

1. Restart the services using:  ::

    systemctl start sssd-kcm.socket
    systemctl start sssd.service

2. Re-run ``omnia.yml`` using: ::

    ansible-playbook omnia.yml

