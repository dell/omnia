Input parameters for the provision tool
-----------------------------------------

Fill in all required parameters in ``input/provision_config.yml``, ``provision_config_credentials.yml``, ``input/software_config.json``.

.. caution:: Do not remove or comment any lines in the above specified ``.yml`` files.

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

    * The following ``admin_network`` details are mandatory:

         * ``nic_name``: The name of the NIC on which the administrative network is accessible to the control plane.
         * ``netmask_bits``: The 32-bit "mask" used to divide an IP address into subnets and specify the network's available hosts.
         * ``static_range``: The static range of IPs to be provisioned on target nodes.
         * ``dynamic_range``: The dynamic range of IPs to be provisioned on target nodes.
         * ``correlation_to_admin``: Boolean value used to indicate whether all other networks specified in the file (for example: ``bmc_network``) should be correlated to the admin network. For example, if a target node is assigned the IP xx.yy.0.5 on the admin network, it will be assigned the IP aa.bb.0.5 on the BMC network. This value is irrelevant when discovering nodes using a mapping file.
         * ``admin_uncorrelated_node_start_ip``: If ``correlation_to_admin`` is set to true but correlated IPs are not available on non-admin networks, provide an IP within the ``static_range`` of the admin network that can be used to assign admin static IPs to uncorrelated nodes. If this is empty, then the first IP in the ``static_range`` of the admin network is taken by default. This value is irrelevant when discovering nodes using a mapping file.
         * ``MTU``: Maximum transmission unit (MTU) is a measurement in bytes of the largest data packets that an Internet-connected device can accept.
         * ``DNS``: A DNS server is a computer equipped with a database that stores the public IP addresses linked to the domain names of websites, enabling users to reach websites using their IP addresses. This is an optional detail.

    * If the ``nic_name`` is identical on both the ``admin_network`` and the ``bmc_network``, it indicates a LOM setup. Otherwise, it's a dedicated setup.
    * BMC network details are not required when target nodes are discovered using a mapping file.
    * If ``bmc_network`` properties are provided, target nodes will be discovered using the BMC method in addition to the methods whose details are explicitly provided in ``provision_config.yml``.
    * The following parameters are applicable for ``bmc_network``:

        * ``discover_ranges``: If some iDRACs are reachable from control_plane but is not in ``bmc_network``, then user can provide those IP ranges here. Discovery of a single IP is not possible. User must provide a range. This is an optional field. User must not remove any of the fields even though it is optional.
        * ``reassignment_to_static``: If iDRACs are set to DHCP mode and Omnia has assigned the IPs, then the user can reassign the IP within the ``bmc_network`` static range by setting this value to ``true``. If this value is not provided or set to ``false`` while the iDRACs are in DHCP mode, they will obtain IPs from the ``bmc_network`` dynamic range, and these IPs will then be converted to static IPs for the iDRACs.

.. caution::
    * Do not assign the subnet 10.4.0.0/24 to any interfaces in the network as nerdctl uses it by default.
    * If a DNS server is available on the network, ensure that the ranges provided in the ``input/network_spec.yml`` file do not include the IP ranges of the DNS server.
    * All provided network ranges and NIC IP addresses should be distinct with no overlap in the ``input/network_spec.yml``.
    * Ensure that all the iDRACs are reachable from the Control Plane.
    * If ``bmc_network`` details are provided, target nodes will be discovered using the BMC method for all network ranges.

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

    * The ``input/provision_config_credentials.yml`` file is encrypted on the first run of the ``discovery_provision.yml`` or ``local_repo.yml`` playbooks.

        To view the encrypted parameters: ::

            ansible-vault view provision_config_credentials.yml --vault-password-file .provision_credential_vault_key

        To edit the encrypted parameters: ::

            ansible-vault edit provision_config_credentials.yml --vault-password-file .provision_credential_vault_key

    * The strings ``admin_network`` and ``bmc_network`` in the ``input/network_spec.yml`` file should not be edited. Also, the properties ``nic_name``, ``static_range``, and ``dynamic_range`` cannot be edited on subsequent runs of the provision tool.
    * Netmask bits are mandatory and should be same for both the ``admin_network`` and ``bmc_network`` (that is, between 1 and 32; 1 and 32 are acceptable values).
    * The ``discover_ranges`` property of the ``bmc_network`` can accept multiple comma-separated ranges.

