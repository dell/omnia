# How to Create a user using Freeipa

## Prerequisites:
1. Make sure the server and client are installed
2. The admin user has to be initialized using kerberos authentication.

   `kinit admin` (When prompted provide the password)
   

## Adding the New User
1. ssh to manager node

	`ssh xxxxx@xx.xx.xx.xx`

2. Use the command below to create a user:

	`ipa user-add '<new username>' --first='<User's first name>'
    --last='<User's last name>' --homedir='Home Directory path (optional)' 
    --random`

3. The output will display the random password set. 
```
 "----------------------",
            "Added user \"omniauser\"",
            "----------------------",
            "  User login: omniauser",
            "  First name: omnia",
            "  Last name: user",
            "  Full name: omnia user",
            "  Display name: omnia user",
            "  Initials: ou",
            "  Home directory: /home/omniauser",
            "  GECOS: omnia user",
            "  Login shell: /bin/sh",
            "  Principal name: omniauser@MYIPA.TEST",
            "  Principal alias: omniauser@MYIPA.TEST",
            "  User password expiration: 20210804180355Z",
            "  Email address: omniauser@myipa.test",
            "  Random password: 0Qr:Ir;:q_vFKP+*b|0)0D",
            "  UID: 893800014",
            "  GID: 893800014",
            "  Password: True",
            "  Member of groups: ipausers",
            "  Kerberos keys available: True"			
			
```
			
4. The random password displayed can be used to log in to the login node using the newly created user.

	` ssh omniauser@192.168.1.6`

5. Change the password on first login and then login with the new password.

6. To assign permissions to the newly created user to execute slurm jobs run the command:

   `usermod -a -G slurm 'new_login_user'`
7. The user has been assigned appropriate permissions to execute slurm jobs. Jobs can be executed

	` srun --nodes 1 --ntasks-per-node 1 --partition normal hostname`

## Mounting user home directories to the NFS Server
### Configuring ipa client services on the NFS server
In order to set up shared user home directories on the NFS server, an authentication service has to be installed on the NFS server. IPA client is used on the NFS share to manage authentication.

1.Run the playbook `install_ipa_client.yml` from the `omnia/tools` folder on the control plane to set up the IPA client on all target nodes: <br>
`ansible-playbook install_ipa_client.yml -i inventory -e kerberos_admin_password="" -e ipa_server_hostname="" -e domain_name="" -e ipa_server_ipadress=""`
| Input Parameter         | Definition                                                      | Variable value                                                                                                                                                                                                                                                    |
|-------------------------|-----------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| kerberos_admin_password | "admin" user password for the IPA server on RockyOS and RedHat. | The password can be found in the file   `omnia/control_plane/input_params/login_vars.yml` when the IPA server is   installed on the control plane. If the IPA server is installed on the manager   node, the value can be found in `omnia/omnia_config.yml`       |
| ipa_server_hostname     | The hostname of the IPA server                                  | The hostname can be found on the IPA server (typically control plane or   manager node) using the `hostname` command                                                                                                                                              |
| domain_name             | Domain name                                                     | The domain name can be found in the file   `omnia/control_plane/input_params/security_vars.yml` when the IPA server is   installed on the control plane. If the IPA server is installed on the manager   node, the value can be found in `omnia/omnia_config.yml` |
| ipa_server_ipadress     | The IP address of the IPA server                                | The IP address can be found on the IPA server (typically control plane or   manager node) using the `ip a` command. This IP address should be accessible   from all target nodes.                                                                                 |

>> **Note**:
>> * The password to the admin account on the IPA server for the management server is available in `control_plane/input_params/login_vars.yml`. If your IPA server is on the login node, the password will be available in `input_params/omnia_config.yml`.
>> * For external NFS servers, ensure that a password-less SSH session is enabled between the control plane and the server. Omnia configures password-less SSH sessions during the run of `control_plane.yml`.
>> * All NFS servers and their prospective clients have to reside in the same domain. Else, this will have to be rectified by the user.
>> * To set up IPA services on all nodes, [click here](../Installation_Guides/ENABLING_OMNIA_FEATURES.md#setting-up-a-centralized-ipa-authentication-service)
2. (Optional) Set up the default home directory for IPA users with the command: `ipa config-mod --homedirectory=/xxxxx/`