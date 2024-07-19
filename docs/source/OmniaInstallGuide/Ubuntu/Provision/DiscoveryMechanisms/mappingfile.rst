mapping
--------------
Manually collect PXE NIC information for target servers and define them to Omnia (using the ``pxe_mapping_file`` variable in ``input/provision_config.yml``) using a mapping file using the below format:

**pxe_mapping_file.csv**


::

    SERVICE_TAG,HOSTNAME,ADMIN_MAC,ADMIN_IP,BMC_IP
    XXXXXXXX,n1,xx:yy:zz:aa:bb:cc,10.5.0.101,10.3.0.101
    XXXXXXXX,n2,aa:bb:cc:dd:ee:ff,10.5.0.102,10.3.0.102

.. note::
    * The header fields mentioned above are case sensitive.
    * The service tags provided are not validated. Ensure the correct service tags are provided.
    * The hostnames provided should not contain the domain name of the nodes.
    * All fields mentioned in the mapping file are mandatory except ``bmc_ip``.
    * The MAC address provided in ``pxe_mapping_file.csv`` should refer to the PXE NIC on the target nodes.
    * If the field ``bmc_ip`` is not populated, manually set the nodes to PXE mode and start provisioning. If the fields are populated and IPMI is enabled, Omnia will take care of provisioning automatically.
    * Target servers should be configured to boot in PXE mode with the appropriate NIC as the first boot device.
    * To assign IPs on the BMC network while discovering servers using a mapping file, target servers should be in DHCP mode or switch details should be provided.

.. caution:: If incorrect details are provided in the mapping file and the same is passed on to the Omnia DB (this takes place when ``discovery.yml`` or ``discovery_provision.yml`` is run), delete the nodes with incorrect information using the `linked script. <../../../Maintenance/deletenode.html>`_ After deletion, provide correct details in the mapping file and re-run ``discovery_provision.yml`` or ``discovery/discovery.yml``. If the ``bmc_ip`` alone is incorrect, manually PXE boot the target server to update the database.

Next step:

* `Provisioning the cluster <../installprovisiontool.html>`_