NFS Bolt On
===========

After an NFS client is configured, if the NFS server is rebooted, the client may not be able to send communications to the server. In those cases, restart the NFS server using the below command:

::

    systemctl disable nfs-server
    systemctl enable nfs-server
    systemctl restart nfs-server



NFS Server
===========

* Ensure that powervault support is enabled by setting ``powervault_support`` to true in ``provision_config.yml``. By default, a volume called 'omnia_home' will be created on the powervault to mount on the nfs_node.

.. warning:: Powervault will only be available over SAS if the powervault has been configured using `powervault.yml <../ConfiguringStorage>`_.

* For multiple NFS volumes, enter the following details in JSON list format in ``powervault_input.yml`` under ``powervault_volumes``:

    - name [Mandatory]: The name of the NFS export.

    - server_share_path [Mandatory]: The path at which volume is mounted on nfs_node. This directory will be assigned 755 permissions during NFS server configuration.

    - server_export_options: (Default) rw,sync,no_root_squash

    - client_shared_path: The path at which volume is mounted on manager, compute, login node. Unless specified otherwise, the client path will inherit the options from the ``server_export_path``.

    - client_mount_options: Default value is- nosuid,rw,sync,hard,intr (unless specified otherwise)

* Only one NFS server is configured per run of ``omnia.yml``. To configure multiple NFS servers, update the following per execution:

  * ``powervault_ip`` in ``omnia_config.yml``

  * nfs_node group IP in the node inventory

* The default entry for ``powervault_volumes`` will look like this:  ``  - { name: omnia_home, server_share_path: /home/omnia_home, server_export_options: ,client_share_path: , client_mount_options: }``

* Ensure that ``powervault_ip`` is populated. The right powervault IP can be found in ``/opt/omnia/powervault_inventory``. If it's not present, run ``ansible-playbook collect_device_info.yml`` (dedicated NIC) or ``ansible-playbook collect_node_info.yml`` (LOM NIC) from the control_plane directory.

.. note:: In a single run of omnia, only one NFS Server is configured. To configure multiple NFS Servers, add one IP in the nfs_node group and populate the variables accordingly per run of ``omnia.yml``. To configure another nfs node, update variables and run ``nfs_sas.yml``.

* If NFS server configuration is to happen via SAS, the following conditions are to be met:

* There should be multiple network paths available between the NFS server and the Powervault to ensure high availability. For more information, `click here <https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/configuring_device_mapper_multipath/overview-of-device-mapper-multipathing_configuring-device-mapper-multipath>`_.

.. image:: ../../images/MultipathingOverSAS.png

* Set ``powervault_protocol`` to 'sas' in ``powervault_input.yml``.

* Configuring NFS over ISCSI is only supported on Powervault ME4.

