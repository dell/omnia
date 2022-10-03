Enabling Security on the Login Node
====================================

Ensure that ``enable_secure_login_node`` is set to **true** in ``omnia_config.yml``

**Limiting User Authentication over sshd**

Users logging into this host can be **optionally** allowed or denied using an access control list. All users to be allowed or denied are to be listed in the variable ``user`` in ``omnia_security_vars.yml``.

.. note:: All users on the server will have to be defined manually. Omnia does not create any users by default.

**Session Timeout**

To encourage security, users who have been idle over 3 minutes will be logged out automatically. To adjust this value, update the ``session_timeout`` variable in ``omnia_security_vars.yml``. This variable is mandatory.

**Restricting Program Support**

Optionally, different communication protocols can be disabled on the control plane using the ``restrict_program_support`` and ``restrict_softwares`` variables in ``omnia_security_vars.yml``. These protocols include: telnet,lpd,bluetooth,rlogin and rexec. Features that cannot be disabled include: ftp,smbd,nmbd,automount and portmap.

.. note:: The parameter ``restrict_softwares`` is **case-sensitive**

**Logging Program Executions using Snoopy**

Omnia installs Snoopy to log all program executions on Linux/BSD systems. For more information on Snoopy, `click here <https://github.com/a2o/snoopy>`_.

**Logging User activity using PSACCT/ACCT**

Using PSACCT on Rocky and Acct on LeapOS, admins can monitor activity. For more information, `click here <https://www.redhat.com/sysadmin/linux-system-monitoring-acct>`_.

**Configuring Email Alerts for Authentication Failures**

If the ``alert_email_address`` variable in ``omnia_security_config.yml`` is populated with a single, valid email ID, all authentication failures will trigger an email notification. A cron job is set up to verify failures and send emails every hour.

.. note:: The ``alert_email_address`` variable is **optional**. If it is not populated, authentication failure email alerts will be disabled.

**Kernel Lockdown**

* RockyOS has Kernel Lockdown mode (Integrity) enabled by default
* SUSE/Leap allows users to set Kernel Lockdown mode to Confidentiality or Integrity.