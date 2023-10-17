mapping
--------------
Manually collect PXE NIC information for target servers and manually define them to Omnia using a mapping file using the below format:

**pxe_mapping_file.csv**


::

    MAC,Hostname,IP

    xx:yy:zz:aa:bb:cc,server,10.5.0.101

    aa:bb:cc:dd:ee:ff,server2, 10.5.0.102

.. note::
    * All the file contents mentioned above are case sensitive. The casing of words like ``[manager]``, ``[compute]``,  etc should be consistent with the samples below when creating inventory or mapping files.
    * The hostnames listed in the above file should be exclusively lower-case with no special characters.
    * The MAC address provided in ``pxe_mapping_file.csv`` should refer to the PXE NIC on the target nodes.

.. caution::
    * Do not remove or comment any lines in the ``input/provision_config.yml`` file.
    * **THE ROCKY LINUX OS VERSION ON THE CLUSTER WILL BE UPGRADED TO THE LATEST 8.x VERSION AVAILABLE IRRESPECTIVE OF THE PROVISION_OS_VERSION PROVIDED IN PROVISION_CONFIG.YML.**
    * ``admin_nic_subnet``, ``ib_nic_subnet`` and ``bmc_nic_subnet`` should have the same subnet mask (Omnia only supports /16 subnet masks currently).

The following parameters need to be populated in ``input/provision_config.yml`` to discover target nodes using a mapping file.

.. csv-table:: Parameters
   :file: ../../../Tables/mapping.csv
   :header-rows: 1

.. [1] Boolean parameters do not need to be passed with double or single quotes.

.. caution:: The IP address *192.168.25.x* is used for PowerVault Storage communications. Therefore, do not use this IP address for other configurations.

.. note::

    The ``input/provision_config.yml`` file is encrypted on the first run of the provision tool:

        To view the encrypted parameters: ::

            ansible-vault view provision_config.yml --vault-password-file .provision_vault_key

        To edit the encrypted parameters: ::

            ansible-vault edit provision_config.yml --vault-password-file .provision_vault_key



To continue to the next steps:

* `Provisioning the cluster <../installprovisiontool.html>`_