Input parameters for the provision tool
-----------------------------------------

Fill in all required parameters in ``input/provision_config.yml``, ``provision_config_credentials.yml``, ``input/software_config.json``.

.. caution:: Do not remove or comment any lines in the ``input/provision_config.yml`` file.

.. csv-table:: provision_config.yml
   :file: ../../Tables/Provision_config.csv
   :header-rows: 1
   :keepspace:

.. csv-table:: provision_config_credentials.yml
   :file: ../../Tables/Provision_creds.csv
   :header-rows: 1
   :keepspace:

.. csv-table:: software_config.json
   :file: ../../Tables/software_config.csv
   :header-rows: 1
   :keepspace:


.. note::

    The ``input/provision_config.yml`` file is encrypted on the first run of the provision tool:

        To view the encrypted parameters: ::

            ansible-vault view provision_config.yml --vault-password-file .provision_vault_key

        To edit the encrypted parameters: ::

            ansible-vault edit provision_config.yml --vault-password-file .provision_vault_key

.. caution::

    * The IP address *192.168.25.x* is used for PowerVault Storage communications. Therefore, do not use this IP address for other configurations.
    * The IP range *x.y.246.1* - *x.y.255.253* (where x and y are provided by the first two octets of ``bmc_nic_subnet``) are reserved by Omnia.