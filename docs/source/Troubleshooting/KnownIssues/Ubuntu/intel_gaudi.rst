Intel Gaudi accelerators
==========================

⦾ **Why does the** ``hl-smi`` **commands fail to detect the Intel Gaudi drivers installed during provisioning?**

.. image:: ../../../images/intel_known_issue.png

**Potential Cause**: This occurs when the Intel Gaudi node has internet access during provisioning. If the node has internet access, the OS kernel gets updated during provisioning which impact the Gaudi driver installation.

**Resolution**: If you encounter the above-mentioned error, run the ``accelerator.yml`` playbook to fix the issue. Omnia recommends to install the Intel Gaudi driver post provisioning using the ``accelerator.yml`` playbook in case the node has internet connectivity during provisioning. For more information, `click here <../../../OmniaInstallGuide/Ubuntu/AdvancedConfigurationsUbuntu/Habana_accelerator.html>`_.