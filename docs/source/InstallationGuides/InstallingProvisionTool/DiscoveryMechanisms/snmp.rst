snmpwalk
----------

Omnia can query known switches (by IP and community string) for information on target node MAC IDs. The following parameters need to be populated in ``input/provision_config.yml`` to discover target nodes using SNMP.

**Pre requisites**

SNMPv2 should be enabled on the switch specified using ``pxe_switch_ip`` in ``input/provision_config``.

To enable SNMPv2, log in to the switch and run the following commands: ::

    configure terminal
    snmp-server community public ro
    exit

Use ``show snmp community`` to verify your changes.

.. note:: The commands provided above sets the SNMP community string of the switch to ``public``. Ensure that the community string set above matches the value provided in ``pxe_switch_snmp_community_string`` in ``input/provision_config.yml``

.. caution::
    * Target servers with LOM architecture is not supported.
    * Do not remove or comment any lines in the ``input/provision_config.yml`` file.
    * ``admin_nic_subnet``, ``ib_nic_subnet`` and ``bmc_nic_subnet`` should have the same subnet mask (Omnia only supports /16 subnet masks currently).
    * **THE ROCKY LINUX OS VERSION ON THE CLUSTER WILL BE UPGRADED TO THE LATEST 8.x VERSION AVAILABLE IRRESPECTIVE OF THE PROVISION_OS_VERSION PROVIDED IN PROVISION_CONFIG.YML.**


.. csv-table:: Parameters
   :file: ../../../Tables/snmpwalk.csv
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