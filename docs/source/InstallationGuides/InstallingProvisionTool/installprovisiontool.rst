Running The Provision Tool
==============================

1. Edit the ``omnia/input/provision_config.yml`` file to update the required variables.

.. warning:: The IP address *192.168.25.x* is used for PowerVault Storage communications. Therefore, do not use this IP address for other configurations.

2. Provided that the ``pxe_mapping_file_path`` is updated as per the provided template (Omnia/examples/pxe_mapping_file.csv), Omnia deploys the control plane and assigns the component roles by executing the ``omnia.yml`` file.  To deploy the Omnia control plane, run the following command ::

    ansible-playbook provision.yml

3. By running ``provision.yml``, the following configurations take place:

    i. All available compute nodes will be PXE booted to have IP addresses and host names as specified in ``omnia/input/provision.yml``.

    ii. All ports required for xCAT to run will be opened (For a complete list, check out the `Security Configuration Document <../../SecurityConfigGuide/PortsUsed/xCAT.html>`_).

    iii. A PostgreSQL database is set up with all relevant cluster information such as MAC IDs, service tags, infiniband IPs, BMC IPs etc.

            To access the DB, run: ::

                        psql -U postgres

                        \c omniadb


            To view the schema being used in the cluster: ``\dn``

            To view the tables in the database: ``\dt``

            To view the contents of the ``nodeinfo`` table: ``select * from cluster.nodeinfo``

    iv. Offline repositories will be created based on the OS being deployed across the cluster.

Once the script is complete, ensure that PXE boot and RAID configurations are set up on remote nodes. Users are then expected to reboot target servers to provision the right OS.

.. note::

    * If the cluster does not have access to the internet, AppStream will not function. Please use the available offline repositories instead.

    * After running ``provision.yml``, the file ``input/provision_config.yml`` will be encrypted. To edit file, use the command: ``ansible-vault edit provision_config.yml --vault-password-file .provision_vault_key``

    * If the ``provision.yml`` is to be used to re-provision target servers, use the following steps:

         * Use ``lsdef -t osimage | grep install-compute`` to get a list of all valid OS profiles.

         * Use ``nodeset all osimage=<selected OS image from previous command>`` to provision the OS on the target server.

         * PXE boot the target server to bring up the OS.

.. warning:: Once xCAT is installed, restart your SSH session to the control plane to ensure that the newly set up environment variables come into effect.