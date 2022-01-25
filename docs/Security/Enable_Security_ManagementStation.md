# Enabling Security on the Management Station and Login Node

## Enabling FreeIPA on the Management Station:

Set the parameter 'enable_security_support' to true in `base_vars.yml`

## Prerequisites Before Enabling FreeIPA:
* Enter the relevant values in `security_vars.yml`:

| Parameter Name | Default Value | Additional Information                                                                                           |
|----------------|---------------|------------------------------------------------------------------------------------------------------------------|
| domain_name    | omnia.test    | The domain name should not contain an underscore ( _ )                                                           |
| realm_name     | omnia.test    | The realm name should follow the following rules per https://www.freeipa.org/page/Deployment_Recommendations <br> * The realm name must not conflict with any other existing Kerberos realm name (e.g. name used by Active Directory). <br> * The realm name should be upper-case (EXAMPLE.COM) version of primary DNS domain name (example.com).  |

* Enter the relevant values in `login_vars.yml`:

| Parameter Name             | Default Value | Additional Information                                                                           |
|----------------------------|---------------|--------------------------------------------------------------------------------------------------|
| directory_manager_password |               | Password of the Directory Manager with full access to the directory for system management tasks. |
| ipa_admin_password         |               | "admin" user password for the IPA server                                                         |



