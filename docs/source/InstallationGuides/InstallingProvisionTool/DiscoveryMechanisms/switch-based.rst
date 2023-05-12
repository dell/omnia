switch_based
-------------

**Pre requisites**

* IP address for ToR switch needs to be provided.

* Switch port range where all BMC NICs are connected should be provided.

* SNMP v3 should be enabled on the switch.

* Non-admin user credentials for the switch need to be provided.

.. note::
    * To create an SNMPv3 user on S series switches (running  OS10), use the following commands:
        - To create SNMP view: ``snmp-server view test_view internet included``
        - To create SNMP group: ``snmp-server group testgroup auth read test_view``
        - To create SNMP users: ``snmp-server user authuser1 testgroup 3 auth sha authpasswd1``
    * To verify the changes made, use the following commands:
        - To view the SNMP views: ``show snmp view``
        - To view the SNMP groups: ``show snmp group``
        - To view the SNMP users: ``show snmp user``
    * For more information on SNMP on S series switch `click here <https://www.dell.com/support/manuals/en-cr/dell-emc-os-9/s3048-on-9.14.2.6-cli-pub/snmp-server-user?guid=guid-dbed1721-656a-4ad4-821c-589dbd371bf9&lang=en-us>`_
    * For more information on SNMP on N series switch `click here <https://www.dell.com/support/kbdoc/en-us/000133707/how-to-configure-snmpv3-on-dell-emc-networking-n-series-switches>`_



* IPMI over LAN needs to be enabled for the BMC.

* BMC NICs should have a static IP assigned or be configured in DHCP mode.

* BMC credentials should be the same across all servers and provided as input to Omnia.

* Target servers should be configured to boot in PXE mode with appropriate NIC as the first boot device.

* The control plane NIC connected to remote servers (through the switch) should be configured with two IPs in a shared LOM set up. This NIC is configured by Omnia with the IP xx.yy.255.254, aa.bb.255.254 (where xx.yy are taken from ``bmc_nic_subnet`` and aa.bb are taken from ``admin_nic_subnet``) when ``discovery_mechanism`` is set to ``switch-based``.

.. image:: ../../../images/ControlPlaneNic.png


.. warning::
    * Do not use daisy chain ports or the port used to connect to the control plane in ``switch_based_details`` in ``input/provision_config.yml``. This can cause IP conflicts on servers attached to potential target ports.
    * Omnia does not validate SNMP switch credentials, if the provision tool is run with incorrect credentials, use the clean-up script and re-run the provision tool with the correct credentials.


.. note::
    * The IP range *x.y.246.1* - *x.y.255.253* (where x and y are provided by the first two octets of ``bmc_nic_subnet``) are reserved by Omnia.
    * If any of the target nodes have a pre-provisioned IP, do not use a ``bmc_subnet`` and/or ``ip_start_range``/``ip_end_range`` that encapsulates the pre-provisioned IP.
        - For example, if there are target nodes hosted at 10.3.0.11 and 10.3.0.12, ``bmc_subnet`` = 10.3.0.0 with ``ip_start_range`` = 10.3.0.1/ ``ip_end_range`` = 10.3.0.255 will cause a conflict with newly assigned servers however, ``bmc_subnet`` = 10.3.0.0 with ``ip_start_range`` = 10.3.0.100/ ``ip_end_range`` = 10.3.0.150 would be accepted. Alternatively, a different subnet would be acceptable,ie ``bmc_subnet`` = 10.13.0.0.

The following parameters need to be populated in ``input/provision_config.yml`` to discover target nodes using a mapping file.

.. csv-table:: Parameters
   :file: ../../../Tables/switch-based.csv
   :header-rows: 1

.. note::

    The ``input/provision_config.yml`` file is encrypted on the first run of the provision tool:
        To view the encrypted parameters: ::

            ansible-vault view provision_config.yml --vault-password-file .provision_vault_key

        To edit the encrypted parameters: ::

            ansible-vault edit provision_config.yml --vault-password-file .provision_vault_key

To clear the configuration on Omnia provisioned switches and ports, `click here <../../../Roles/Utils/portcleanup.html>`_.



To continue to the next steps:

* `Provisioning the cluster <../installprovisiontool.html>`_