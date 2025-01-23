Input parameters for the provision tool
-----------------------------------------

Fill in all required parameters in ``input/provision_config.yml``, ``input/provision_config_credentials.yml``, ``input/software_config.json``, and ``input/network_spec.yml``.

.. caution:: Do not remove or comment any lines in the above mentioned ``.yml`` files.

.. csv-table:: provision_config.yml
   :file: ../../../Tables/Provision_config.csv
   :header-rows: 1
   :keepspace:

.. [1] Boolean parameters do not need to be passed with double or single quotes.

.. csv-table:: provision_config_credentials.yml
   :file: ../../../Tables/Provision_creds.csv
   :header-rows: 1
   :keepspace:

.. note::

    * The ``input/provision_config_credentials.yml`` file is encrypted on the first execution of the ``discovery_provision.yml`` or ``local_repo.yml`` playbooks.

        * To view the encrypted parameters: ::

            ansible-vault view provision_config_credentials.yml --vault-password-file .provision_credential_vault_key

        * To edit the encrypted parameters: ::

            ansible-vault edit provision_config_credentials.yml --vault-password-file .provision_credential_vault_key


.. csv-table:: software_config.json
   :file: ../../../Tables/software_config_rhel.csv
   :header-rows: 1
   :keepspace:


.. csv-table:: network_spec.yml
   :file: ../../../Tables/network_spec.csv
   :header-rows: 1
   :keepspace:

.. note::

    * If the ``nic_name`` is identical on both the ``admin_network`` and the ``bmc_network``, it indicates a LOM setup. Otherwise, it's a dedicated setup.
    * BMC network details are not required when target nodes are discovered using a mapping file.
    * If ``bmc_network`` properties are provided, target nodes will be discovered using the BMC method in addition to the methods whose details are explicitly provided in ``provision_config.yml``.
    * The strings ``admin_network`` and ``bmc_network`` in the ``input/network_spec.yml`` file should not be edited. Also, the properties ``nic_name``, ``static_range``, and ``dynamic_range`` cannot be edited on subsequent runs of the provision tool.
    * ``netmask_bits`` are mandatory and should be same for both ``admin_network`` and ``bmc_network`` (that is, between 1 and 32; 1 and 32 are also acceptable values).

.. caution::
    * Do not assign the subnet 10.4.0.0/24 to any interfaces in the network as nerdctl uses it by default.
    * All provided network ranges and NIC IP addresses should be distinct with no overlap in the ``input/network_spec.yml``.
    * Ensure that all the iDRACs are reachable from the OIM.

A sample of the ``input/network_spec.yml`` where nodes are discovered using a mapping file is provided below: ::

    ---
         Networks:
         - admin_network:
             nic_name: "eno1"
             netmask_bits: "16"
             static_range: "10.5.0.1-10.5.0.200"
             dynamic_range: "10.5.1.1-10.5.1.200"
             correlation_to_admin: true
             admin_uncorrelated_node_start_ip: "10.5.0.50"
             network_gateway: ""
             DNS: ""
             MTU: "1500"

         - bmc_network:
             nic_name: ""
             netmask_bits: ""
             static_range: ""
             dynamic_range: ""
             reassignment_to_static: true
             discover_ranges: ""
             network_gateway: ""
             MTU: "1500"

A sample of the ``input/network_spec.yml`` where nodes are discovered using BMC discovery mechanism is provided below: ::

    ---
        Networks:
        - admin_network:
            nic_name: ""
            netmask_bits: ""
            static_range: ""
            dynamic_range: ""
            correlation_to_admin: true
            admin_uncorrelated_node_start_ip: ""
            network_gateway: ""
            DNS: ""
            MTU: ""

        - bmc_network:
            nic_name: "eno1"
            netmask_bits: "16"
            static_range: "10.3.0.1-10.3.0.200"
            dynamic_range: "10.3.1.1-10.3.1.200"
            reassignment_to_static: true
            discover_ranges: ""
            network_gateway: ""
            MTU: "1500"