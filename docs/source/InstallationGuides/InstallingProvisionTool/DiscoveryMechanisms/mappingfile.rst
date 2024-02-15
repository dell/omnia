mapping
--------------
Manually collect PXE NIC information for target servers and define them to Omnia using a mapping file using the below format:

**pxe_mapping_file.csv**


::

    SERVICE_TAG,HOSTNAME,ADMIN_MAC,ADMIN_IP,BMC_IP
    6XCVT4,n1,xx:yy:zz:aa:bb:cc,10.5.0.101,10.3.0.101
    V345H5,n2,aa:bb:cc:dd:ee:ff,10.5.0.102,10.3.0.102

.. note::
    * The header fields mentioned above are case sensitive.
    * The service tags provided are not validated. Ensure the correct service tags are provided.
    * The hostnames provided should not contain the domain name of the nodes.
    * All fields mentioned in the mapping file are mandatory except ``bmc_ip``.
    * The MAC address provided in ``pxe_mapping_file.csv`` should refer to the PXE NIC on the target nodes.
    * If the field ``bmc_ip`` is not populated, manually set the nodes to PXE mode and start provisioning. If the fields are populated, Omnia will take care of provisioning automatically.

.. caution::
    * Do not remove or comment any lines in the ``input/provision_config.yml`` file.
    * **THE ROCKY LINUX OS VERSION ON THE CLUSTER WILL BE UPGRADED TO THE LATEST 8.x VERSION AVAILABLE IRRESPECTIVE OF THE PROVISION_OS_VERSION PROVIDED IN PROVISION_CONFIG.YML.**
    * ``admin_nic_subnet``, ``ib_nic_subnet`` and ``bmc_nic_subnet`` should have the same subnet mask (Omnia only supports /16 subnet masks currently).

The following parameters need to be populated in ``input/provision_config.yml`` and ``input/provision_config_credentials.yml``  to discover target nodes using a mapping file.

.. csv-table:: Parameters for Mapping file configuration
   :file: ../../../Tables/mapping.csv
   :header-rows: 1

.. [1] Boolean parameters do not need to be passed with double or single quotes.

.. csv-table:: Credentials for Mapping file configuration
   :file: ../../../Tables/Provision_creds.csv
   :header-rows: 1

.. caution:: The IP address *192.168.25.x* is used for PowerVault Storage communications. Therefore, do not use this IP address for other configurations.

.. note::

    The ``input/provision_config.yml`` file is encrypted on the first run of the provision tool:

        To view the encrypted parameters: ::

            ansible-vault view provision_config.yml --vault-password-file .provision_vault_key

        To edit the encrypted parameters: ::

            ansible-vault edit provision_config.yml --vault-password-file .provision_vault_key



To continue to the next steps:

* `Provisioning the cluster <../installprovisiontool.html>`_