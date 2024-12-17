Intel Gaudi accelerators
==========================

⦾ **Why does the** ``hl-smi`` **command fail to detect the Intel Gaudi drivers installed during provisioning?**

.. image:: ../../../images/intel_known_issue.png

**Potential Cause**: This occurs when the Intel Gaudi node has internet access during provisioning. If the node has internet access, the OS kernel gets updated during provisioning which impact the Gaudi driver installation.

**Resolution**: If you encounter the above-mentioned error, run the ``accelerator.yml`` playbook to fix the issue. Omnia recommends to install the Intel Gaudi driver post provisioning using the ``accelerator.yml`` playbook in case the node has internet connectivity during provisioning. For more information, `click here <../../../OmniaInstallGuide/Ubuntu/AdvancedConfigurationsUbuntu/Habana_accelerator.html>`_.

⦾ **Why does the power stress test using** `Habana Labs Qualification Tool (hl_qual) <https://docs.habana.ai/en/latest/Management_and_Monitoring/Qualification_Library/index.html>`_ **fail for nodes with Intel Gaudi 3 accelerators?**

**Resolution**: This is a known issue, and fix is expected in the upcoming Intel firmware release.

⦾ **Why are only 7 Intel accelerators displayed after a cluster reboot?**

**Potential Cause**: This issue occurs when the initialization of High Bandwidth Memory (HBM) fails for Intel Gaudi accelerators, often due to factors like low voltage or memory limitations.

**Resolution**: This is a known issue, and fix is expected in the upcoming Intel firmware release.