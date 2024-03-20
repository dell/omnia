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


Update the ``input/network_spec.yml`` file for all networks available for use by the control plane.

    * The following ``admin_nic`` details are mandatory.
         * ``nic_name``: The name of the NIC on which the administrative network is accessible to the control plane.
         * ``netmask_bits``: The 32-bit "mask" used to divide an IP address into subnets and specify the network's available hosts.
         * ``static_range``: The static range of IPs to be provisioned on target nodes.
         * ``dynamic_range``: The dynamic range of IPs to be provisioned on target nodes.
         * ``correlation_to_admin``: Boolean value used to indicate whether all other networks specified in the file (eg: ``bmc_network``) should be correlated to the admin network. For eg: if a target node is assigned the IP xx.yy.0.5 on the admin network, it will be assigned the IP aa.bb.0.5 on the BMC network. This value is irrelevant when discovering nodes using a mapping file.
         * ``admin_uncorrelated_node_start_ip``: If ``correlation_to_admin`` is set to true but correlated IPs are not available on non-admin networks, provide an IP within the ``static_range`` of the admin network that can be used to assign admin static IPs to uncorrelated nodes. If this is empty, then the first IP in the ``static_range`` of the admin network is taken by default. This value is irrelevant when discovering nodes using a mapping file.
         * ``CIDR``: Classless or Classless Inter-Domain Routing (CIDR) addresses use variable length subnet masking (VLSM) to alter the ratio between the network and host address bits in an IP address.
         * ``MTU``: Maximum transmission unit (MTU) is a measurement in bytes of the largest data packets that an Internet-connected device can accept.
         * ``DNS``: A DNS server is a computer equipped with a database that stores the public IP addresses linked to the domain names of websites, enabling users to reach websites using their IP addresses.
         * ``VLAN``: A 12-bit field that identifies a virtual LAN (VLAN) and specifies the VLAN that an Ethernet frame belongs to.

    * If the ``nic_name`` is the same on both the admin_network and the bmc_network, a LOM setup is assumed.
    * BMC network details are not required when target nodes are discovered using a mapping file.
    * If ``bmc_network`` properties are provided, target nodes will be discovered using the BMC method in addition to the methods whose details are explicitly provided in ``provision_config.yml``.


A sample is provided below: ::

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





.. note::

    * The ``input/provision_config_credentials.yml`` file is encrypted on the first run of the provision tool:

        To view the encrypted parameters: ::

            ansible-vault view provision_config_credentials.yml --vault-password-file .provision_vault_key

        To edit the encrypted parameters: ::

            ansible-vault edit provision_config_credentials.yml --vault-password-file .provision_vault_key

    * The strings ``admin_network`` and ``bmc_network`` in the ``input/network_spec.yml`` file should not be edited. Also, the properties ``nic_name``, ``static_range``, and ``dynamic_range`` cannot be edited on subsequent runs of the provision tool.
    * Netmask bits are mandatory and should be same for both the ``admin_network`` and ``bmc_network`` (ie between 1 and 32; 1 and 32 are acceptable values).
    * Ensure that the CIDR is aligned with the ``netmask_bits`` provided.
    * The ``discover_ranges`` property of the ``bmc_network`` can accept multiple comma-separated ranges.
    * The ``VLAN`` property is optional but should be between 0 and 4095 (0 and 4095 are not acceptable values).

