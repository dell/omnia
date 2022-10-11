How to Create a User Using Freeipa
====================================

**Prerequisites**

1. Make sure the server and client are installed

2. The admin user has to be initialized using kerberos authentication.

   ``kinit admin`` (When prompted provide the password)

**Adding new users**

1. ssh to manager node

	``ssh xxxxx@xx.xx.xx.xx``

2. Use the command below to create a user:

	``ipa user-add '<new username>' --first='<User's first name>' --last='<User's last name>' --homedir='Home Directory path (optional)' --random``

3. The output will display the random password set.::



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



4. The random password displayed can be used to log in to the login node using the newly created user.

	``ssh omniauser@xx.xx.xx.xx``

5. Change the password on first login and then login with the new password.

6. To assign permissions to the newly created user to execute slurm jobs run the command:

   ``usermod -a -G slurm 'new_login_user'``

7. The user has been assigned appropriate permissions to execute slurm jobs. Jobs can be executed

	``srun --nodes 1 --ntasks-per-node 1 --partition normal hostname``

