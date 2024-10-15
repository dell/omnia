Intel Gaudi accelerators
==========================

⦾ **In Kubeflow 1.9, users cannot select Intel Gaudi3 accelerators from the GPU list while creating a new notebook using the JupyterLab's Kubeflow notebook creation UI.**

**Resolution**: Until this issue is addressed in Kubeflow 1.9.1, it's recommended to avoid using notebooks. Instead, use MPIJobs for Gaudi3 accelerators, which functions correctly.

⦾ **Why does the** ``hl-smi`` **commands fail to detect the Intel Gaudi drivers installed during provisioning?**

.. image:: ../../../images/intel_known_issue.png

**Potential Cause**: This occurs when the Intel Gaudi node has internet access during provisioning. If the node has internet access, the OS kernel gets updated during provisioning which impact the Gaudi driver installation.

**Resolution**: Omnia recommends to install the Intel Gaudi driver post provisioning using the ``accelerator.yml`` playbook in case the node has internet connectivity during provisioning. For more information, `click here <../../../OmniaInstallGuide/Ubuntu/AdvancedConfigurationsUbuntu/Habana_accelerator.html>`_.