Provision
==========

⦾ **Why does the provisioning status of RHEL/Rocky Linux remote servers remain stuck at ‘installing’ in cluster.nodeinfo (omniadb)?**

.. image:: ../../../images/InstallingStuckDB.png

.. image:: ../../../images/InstallCorruptISO.png

**Potential Causes**:

    * Disk partition may not have enough storage space per the requirements specified in ``input/provision_config`` (under ``disk_partition``).

    * The provided ISO may be corrupt/incomplete.

    * Hardware issues (Auto reboot may fail at POST)

    * A virtual disk may not have been created

    * Re-run of the ``discovery_provision.yml`` playbook on the control plane while provisioning is in-progress on the remote nodes.


**Resolution**:

    * Add more space to the server or modify the requirements specified in ``input/provision_config`` (under ``disk_partition``).

    * Download the ISO again, verify the checksum/ download size and re-run the provision tool.

    * Resolve/replace the faulty hardware and PXE boot the node.

    * Create a virtual disk and PXE boot the node.

    * Initiate PXE boot on the remote node after completion of the ``discovery_provision.yml`` playbook execution.