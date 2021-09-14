To Create a user using Freeipa

Prerequisites:
1. Make sure server and client are installed
2. admin has to be initialized using kerberos authentication.
   kinit admin
   When prompted provide the password
3. Create an inventory file with manager group and corresponding node entry
   Eg: [manager]
        192.168.1.5

Usage:
1. Enter the username, user's first name and last name in vars/main.yml
Make sure the username is in small case.
2. Execute playbook using the following command,
ansible-playbook implement_login_node.yml -i inventory
3. The output displays the random password set. 
Eg: "stdout_lines": [
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
        ]
4. The random password displayed can be used to login to the login node using the newly created user.
Eg: ssh omniauser@192.168.1.6
5. Change the password on first login and then login with the new password.
6. The user has been assigned appropriate permissions to execute slurm jobs. Jobs can be executed
Eg: srun --nodes 1 --ntasks-per-node 1 --partition normal hostname
