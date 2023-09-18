Configuring servers with out-of-band management
+++++++++++++++++++++++++++++++++++++++++++++++

For pre-configured iDRACs, ``provision/idrac.yml`` can be used to provision the servers.

**Before running idrac.yml**

* The idrac_inventory file is updated with the iDRAC IP addresses.

* To customize iDRAC provisioning, input parameters can be updated in the ``provision/idrac_input.yml`` file.

* The Lifecycle Controller Remote Services of PowerEdge Servers is in the 'ready' state.

* The Redfish services are enabled in the iDRAC settings under Services.

* The provision tool has discovered the servers using SNMP/mapping.

* iDRAC 9 based Dell EMC PowerEdge Servers with firmware versions 5.00.10.20 and above. (With the latest BIOS available)


**Configurations performed by idrac.yml**

* If bare metal servers have BOSS controllers installed, virtual disks (Data will be stored in a RAID 1 configuration by default) will be created on the BOSS controller (ie, RAID controllers will be ignored/unmanaged). Ensure that exactly 2 SSD disks are available on the server.

* If bare metal servers have a RAID controller installed, Virtual disks are created for RAID configuration (Data will be saved in a RAID 0 configuration by default).

* Omnia validates and configures the active host NICs in PXE device settings when provision_method is set to PXE. (If no active NIC is found, idrac.yml will fail on the target node.)

* Once all configurations are in place, the ``idrac.yml`` initiates a PXE boot for configuration to take effect.

.. note::
    * Servers that have not been discovered by the Provision tool will not be provisioned with the OS image.
    * Since the BMC discovery method PXE boots target iDRACs while running the provision tool, this script is not recommended for such servers.


**Running idrac.yml**

::

    ansible-playbook idrac.yml -i idrac_inventory -e idrac_username='' -e idrac_password=''

Where the ``idrac_inventory`` points to the file mentioned above and  the ``idrac_username`` and ``idrac_password`` are the credentials used to authenticate into iDRAC.



