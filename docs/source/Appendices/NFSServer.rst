Setting up an NFS server
--------------------------

1. Install the required NFS utilities package using: ::

    sudo dnf install -y nfs-utils

2. Create an NFS share using the following commands:

    a. Create a shared folder: ``mkdir /nfs-share``
    b. Move all the files to be shared here. (Use the ``mv`` or ``cp`` command)
    c. Change the permissions on these files: ``sudo chmod -R 777 /nfs-share``

        - For ease, we use ``chmod -R 777``, which sets the local file permissions to read/write/execute for everyone. This minimalizes the need for additional NFS share options in this exercise where the UID/GUID of the client user does not match the server and defaults to the nobody account on the server.

        - Evaluate if these permissions are appropriate for your environment before using them in production.

        - For more details, use ``man nfs``.

    d. Make an entry in ``/etc/exports`` using the format ``<export folder> host1(options1) host2(options2) host3(options3)``. Alternatively, use the below command: ::

            echo "/nfs-share  <CLIENT_IP_ADDRESS>(rw)" | sudo tee -a /etc/exports > /dev/null

3. Update the firewall settings to allow NFS traffic: ::

    sudo firewall-cmd --permanent --zone=public --add-service=nfs
    sudo firewall-cmd --reload
    sudo firewall-cmd --list-all

4. Enable and start the NFS service: ::

    sudo systemctl enable --now nfs-server

5. Use ``showmount -e`` to verify the NFS shares available from the server.


