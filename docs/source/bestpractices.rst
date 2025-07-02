Best Practices
==============

* Ensure that PowerCap policy is disabled and the BIOS system profile is set to 'Performance' on the OIM.
* Always run playbooks from the directory where they are located. Use the ``cd`` command to navigate to the playbook's directory before executing it.
* Omnia recommends using an NFS share with at least 100GB storage.
* Use a `PXE mapping file <OmniaInstallGuide/samplefiles.html#pxe-mapping-file-csv>`_ even when using DHCP configuration to ensure that IP assignments remain persistent across OIM reboots.
* Avoid rebooting the OIM as much as possible to to prevent disruptions to the network configuration.
* Review all the prerequisites before running Omnia playbooks.
* Ensure that the firefox version being used on the RHEL OIM is the latest available. This can be achieved using ``dnf update firefox -y``
* It is recommended to configure devices using Omnia playbooks for better interoperability and ease of access.
* Run ``yum update --security`` routinely on the RHEL OIM for the latest security updates.