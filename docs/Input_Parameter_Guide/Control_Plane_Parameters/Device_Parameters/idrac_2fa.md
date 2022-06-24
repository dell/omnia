# Parameters in `idrac_2fa.yml`
This file is located in [/control_plane/tools](../../../../control_plane/tools/idrac_2fa.yml)

|	Variables</br> [Required if two_factor_authentication is enabled/ Optional]	|	Default, choices	|	Description
----------------	|	-----------------	|	-----------------
dns_domain_name</br> [Required]	|		|	DNS domain name to be set for iDRAC. 
ipv4_static_dns1, ipv4_static_dns2</br> [Required] 	|		|	DNS1 and DNS2 static IPv4 addresses.
smtp_server_ip</br> [Required]	|		|	Server IP address used for SMTP.
use_email_address_2fa</br> [Required]	|		|	Email address used for enabling 2FA. After 2FA is enabled, an authentication code is sent to the provided email address. 
smtp_authentication [Required]	| <ul> <li>__Disabled__</li> <li>Enabled </li> </ul> | Enable SMTP authentication 
smtp_username</br> [Optional]	|		|	Username for SMTP.
smtp_password</br> [Optional]	|		|	Password for SMTP.