Security
=========

⦾ **Why don't IPA commands work after setting up FreeIPA on the cluster?**

**Potential Cause**: Kerberos authentication may be missing on the target node.

**Resolution**: Run ``kinit admin`` on the node and provide the ``kerberos_admin_password`` when prompted. (This password is also entered in ``input/security_config.yml``)

