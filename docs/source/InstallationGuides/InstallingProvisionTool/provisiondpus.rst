Configuring DPUs with out-of-band management
+++++++++++++++++++++++++++++++++++++++++++++++

For pre-configured DPU BMCs, ``provision/bluefield.yml`` can be used to provision the DPUs.

**Before running bluefield.yml**

* The dpu_bmc_inventory file is updated with the DPU BMC IP addresses.

* The Redfish services are enabled in the DPU BMC settings under Services.

* The provision tool has discovered the DPUs using SNMP/mapping.


**Configurations performed by bluefield.yml**

* Omnia validates and configures the active DPU NICs in PXE device settings when provision_method is set to PXE. (If no active NIC is found, bluefield.yml will fail on the target node.)

* Once all configurations are in place, the ``bluefield.yml`` initiates a PXE boot for configuration to take effect.

.. note::
    * DPUs that have not been discovered by the Provision tool will not be provisioned with the OS image.
    * Since the BMC discovery method PXE boots target DPU BMCs while running the provision tool, this script is not recommended for such DPUs.


**Running bluefield.yml**

::

    ansible-playbook bluefield.yml -i dpu_bmc_inventory -e dpu_bmc_username='' -e dpu_bmc_password=''

Where the ``dpu_bmc_inventory`` points to the file mentioned above and  the ``dpu_bmc_username`` and ``dpu_bmc_password`` are the credentials used to authenticate into DPU BMC.



