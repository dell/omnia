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

.. [1] Boolean parameters do not need to be passed with double or single quotes.


Update the ``input/network_spec.yml`` file for all networks available for use by the control plane. A sample is provided below: ::

     ---
     Networks:
       - admin_network:
           nic_name: "eno1"
           netmask_bits: "16"
           static_range: "10.5.0.1-10.5.0.200"
           dynamic_range: "10.5.1.1-10.5.1.200"
           network_gateway: ""
           DNS: ""
           MTU: "1500"

       - bmc_network:
           nic_name: ""
           netmask_bits: ""
           static_range: ""
           dynamic_range: ""
           discover_ranges: ""
           network_gateway: ""
           MTU: "1500"

.. note::

    The ``input/provision_config.yml`` file is encrypted on the first run of the provision tool:

        To view the encrypted parameters: ::

            ansible-vault view provision_config.yml --vault-password-file .provision_vault_key

        To edit the encrypted parameters: ::

            ansible-vault edit provision_config.yml --vault-password-file .provision_vault_key

.. caution::

    * The IP address *192.168.25.x* is used for PowerVault Storage communications. Therefore, do not use this IP address for other configurations.
    * The IP range *x.y.246.1* - *x.y.255.253* (where x and y are provided by the first two octets of ``bmc_nic_subnet``) are reserved by Omnia.