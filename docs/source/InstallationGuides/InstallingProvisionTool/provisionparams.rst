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

       #   - thor_network1:
       #       netmask_bits: "20"
       #       CIDR: "10.10.16.0"
       #       network_gateway: ""
       #       MTU: "1500"
       #       VLAN: ""

       #   - thor_network2:
       #       netmask_bits: "20"
       #       static_range: "10.10.1.1-10.10.15.254"
       #       network_gateway: ""
       #       MTU: "1500"
       #       VLAN: "1"

.. note::

    * The ``input/provision_config_credentials.yml`` file is encrypted on the first run of the provision tool:

        To view the encrypted parameters: ::

            ansible-vault view provision_config_credentials.yml --vault-password-file .provision_vault_key

        To edit the encrypted parameters: ::

            ansible-vault edit provision_config_credentials.yml --vault-password-file .provision_vault_key

    * The strings ``admin_network`` and ``bmc_network`` in the ``input/network_spec.yml`` file should not be edited. Also, the properties ``nic_name``, ``static_range``, and ``dynamic_range`` cannot be edited on subsequent runs of the provision tool.
    * Netmask bits is mandatory and should be same for both the ``admin_network`` and ``bmc_network`` (ie between 1 and 32; 1 and 32 are acceptable values).
    * Ensure that the CIDR is aligned with the ``netmask_bits`` provided.
    * The ``discover_ranges`` property of the ``bmc_network`` can accept multiple comma-separated ranges.
    * The ``VLAN`` property is optional but should be between 0 and 4095 (0 and 4095 are not acceptable values).

