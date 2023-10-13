bmc
---

For automatic provisioning of servers and discovery, the BMC method can be used.

**Pre requisites**

* Set the IP address of the control plane with a /16 subnet mask. The control plane NIC connected to remote servers (through the switch) should be configured with two IPs (BMC IP and admin IP) in a shared LOM or hybrid set up. In the case dedicated network topology, a single IP (admin IP) is required.
.. image:: ../../../images/ControlPlaneNic.png

* BMC NICs should have a static IP assigned or be configured in DHCP mode.

* BMC credentials should be the same across all servers and provided as input to Omnia in the parameters explained below.

* Target servers should be configured to boot in PXE mode with the appropriate NIC as the first boot device.

* IPMI over LAN needs to be enabled for the BMC. ::

    racadm set iDRAC.IPMILan.Enable 1
    racadm get iDRAC.IPMILan

- IP ranges (``bmc_static_start_range``, ``bmc_static_start_range``) provided to Omnia for BMC discovery should be within the same subnet.

.. caution::
    * To create a meaningful range of discovery, ensure that the last two octets of   ``bmc_static_end_range`` are equal to or greater than the last two octets of   the ``bmc_static_start_range``. That is, for the range a.b.c.d - a.b.e.f, e   and f should be greater than or equal to c and d. *Ex: 172.20.0.50 -   172.20.1.101 is a valid range however,    172.20.0.101 - 172.20.1.50 is not.*
    * If you are re-provisioning your cluster (that is, re-running the ``provision.yml`` playbook) after a `clean-up <../../CleanUpScript.html>`_, ensure to use a different ``admin_nic_subnet`` in ``input/provision_config.yml`` to avoid a conflict with newly assigned servers. Alternatively, disable any OS available in the ``Boot Option Enable/Disable`` section of your BIOS settings (``BIOS Settings`` > ``Boot Settings`` > ``UEFI Boot Settings``) on all target nodes.
    * ``admin_nic_subnet``, ``ib_nic_subnet`` and ``bmc_nic_subnet`` should have the same subnet mask (Omnia only supports /16 subnet masks currently).

- All iDRACs should be reachable from the ``admin_nic``.

.. note::
    *When iDRACs are in DHCP mode**
        *  The IP range *x.y.246.1* - *x.y.255.253* (where x and y are provided by the first two octets of ``bmc_nic_subnet``) are reserved by Omnia.
        * *x.y.246.1* - *x.y.250.253* will be the range of IPs reserved for dynamic assignment by Omnia.
        * During provisioning, Omnia updates servers to static mode and assigns IPs from *x.y.251.1* - *x.y.255.253*.
        * Users can see the IPs (that have been assigned from *x.y.251.1* - *x.y.255.253*) in the DB after provisioning the servers.
        * For example:
            If the provided ``bmc_subnet`` is ``10.3.0.0`` and there are two iDRACs in DHCP mode, the IPs assigned will be ``10.3.251.1`` and ``10.3.251.2``.

The following parameters need to be populated in ``input/provision_config.yml`` to discover target nodes using BMC.

.. caution::
    * Do not remove or comment any lines in the ``input/provision_config.yml`` file.
    * **THE ROCKY LINUX OS VERSION ON THE CLUSTER WILL BE UPGRADED TO THE LATEST 8.x VERSION AVAILABLE IRRESPECTIVE OF THE PROVISION_OS_VERSION PROVIDED IN PROVISION_CONFIG.YML.**

.. csv-table:: Parameters
   :file: ../../../Tables/bmc.csv
   :header-rows: 1
   :keepspace:

.. [1] Boolean parameters do not need to be passed with double or single quotes.

.. note::

    The ``input/provision_config.yml`` file is encrypted on the first run of the provision tool:

        To view the encrypted parameters: ::

            ansible-vault view provision_config.yml --vault-password-file .provision_vault_key

        To edit the encrypted parameters: ::

            ansible-vault edit provision_config.yml --vault-password-file .provision_vault_key




.. caution:: The IP address *192.168.25.x* is used for PowerVault Storage communications. Therefore, do not use this IP address for other configurations.


To continue to the next steps:

* `Provisioning the cluster <../installprovisiontool.html>`_