Security
=========

⦾ **What to do when omnia.yml fails while completing the security role, and returns the following error message: 'Error: kinit: Connection refused while getting default cache'?**

**Resolution**:

1. Start the sssd-kcm.socket: ``systemctl start sssd-kcm.socket``

2. Re-run ``omnia.yml``