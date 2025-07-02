mapping
--------------
Manually collect PXE NIC information for target servers and manually define them to Omnia using the **pxe_mapping_file.csv** file. Provide the filepath to the ``pxe_mapping_file`` variable in ``input/project_default/provision_config.yml``. A sample format of the mapping file is shown below:

::

    GROUP_NAME,SERVICE_TAG,HOSTNAME,ADMIN_MAC,ADMIN_IP,BMC_IP
    grp0,XXXXXXXX,n1,xx:yy:zz:aa:bb:cc,10.5.0.101,10.3.0.101
    grp0,XXXXXXXX,n2,aa:bb:cc:dd:ee:ff,10.5.0.102,10.3.0.102

.. note::
    * The header fields mentioned above are case sensitive.
    * The service tags provided in the mapping file are not validated by Omnia. Ensure that correct service tags are provided. Incorrect service tags can cause unexpected failures.
    * The hostnames provided should not contain the domain name of the nodes.
    * All fields mentioned in the mapping file are mandatory except ``bmc_ip``.
    * The MAC address provided in ``pxe_mapping_file.csv`` should refer to the PXE NIC on the target nodes.
    * If the field ``bmc_ip`` is not populated, manually set the nodes to PXE mode and start provisioning. If the fields are populated and IPMI is enabled, Omnia will take care of provisioning automatically.
    * Target servers should be configured to boot in PXE mode with the appropriate NIC as the first boot device.
    * To assign IPs on the BMC network while discovering servers using a mapping file, target servers should be in DHCP mode or switch details should be provided.

.. caution:: If incorrect details are provided in the mapping file and the same is passed on to the ``OmniaDB`` (during ``discovery_provision.yml`` playbook execution), you must first delete the nodes with incorrect information using the `delete_node.yml <../../../Maintenance/deletenode.html>`_ script. After deletion, provide correct details in the mapping file and re-run the ``discovery_provision.yml`` playbook. If only the ``bmc_ip`` is incorrect, manually PXE boot the cluster node and the database will be updated automatically with the correct information.

Next step:

* `Provisioning the cluster <../installprovisiontool.html>`_