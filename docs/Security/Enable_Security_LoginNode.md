# Enabling Security on the Login Node (RockyOS)

* Ensure that `enable_secure_login_node` is set to **true** in `omnia_config.yml`
* Set the following parameters in `omnia_security_config.yml`

|  Parameter Name        |  Default Value  |  Additional Information                                                                                                                                          |
|------------------------|-----------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| max_failures           | 3               | Failures allowed before lockout. <br> This value cannot currently   be changed.                                                                                  |
| failure_reset_interval | 60              | Period (in seconds) after which the number of failed login attempts is   reset <br> Accepted Values: 30-60                                                       |
| lockout_duration       | 10              | Period (in seconds) for which users are locked out. <br> Accepted   Values: 5-10                                                                                 |
| session_timeout        | 180             | Period (in seconds) after which idle users get logged out automatically   <br> Accepted Values: 30-90                                                            |
| alert_email_address    |                 | Email address used for sending alerts in case of authentication failure   <br> If this variable is left blank, authentication failure alerts will   be disabled. |
| allow_deny             | Allow           | This variable sets whether the user list is Allowed or Denied. <br>   Accepted Values: Allow, Deny                                                               |
| user                   |                 | Array of users that are allowed or denied based on the `allow_deny`   value. Multiple users must be separated by a space.                                        |

