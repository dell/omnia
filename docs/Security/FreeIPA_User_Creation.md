# How to Create a user using Freeipa

## Prerequisites:
1. Make sure the server and client are installed
2. The admin user has to be initialized using kerberos authentication.

   `kinit admin` (When prompted provide the password)
   

## Adding the New User
1. ssh to manager node

	`ssh xxxxx@192.168.1.5`

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

## Mounting user home directories to the NFS Share
### Configuring ipa client services on the NFS node
1. Log into the NFS node using any user account.
2. Update `/etc/host` with the IPA server host details. <br>
```text
vi /etc/hosts 
xx.xx.xx.xx  ipaserver.omnia.test
```
3. Use dnf to install ipa-client on the NFS server. <br>
`dnf install ipa-client -y`
4. Configure ipa-client services using the following command: <br>
`ipa-client-install --domain omnia.test --server ipaserver.omnia.test --principal admin --password kerberos --force-join --enable-dns-updates --force-ntpd --mkhomedir -U`

>> **Note**:
>> * The password to the admin account on the IPA server for the management server is available in `control_plane/input_params/login_vars.yml`. If your IPA server is on the login node, the password will be available in `input_params/omnia_config.yml`.
>> * The IPA server and the target cluster nodes do not have to be in the same domain. However, the server has to be reachable to all nodes.

5. (Optional) Set up the default home directory for IPA users with the command: `ipa config-mod --homedirectory=/mnt/users/ `