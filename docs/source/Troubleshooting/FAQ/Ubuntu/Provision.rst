Provision
===========

⦾ **Why does the provisioning status of Ubuntu remote servers remain stuck at ‘bmcready’ or 'powering-on' in cluster.nodeinfo (omniadb)?**

.. image:: ../../../images/ubuntu_pxe_failure.png

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


⦾ **Why does the provisioning status of Kubernetes RoCE pod remain stuck at 'Pending' or 'ContainerCreating' state?**

.. image:: ../../../images/roce_pod_failure.png

**Potential Cause**: This issue is encountered if incorrect parameter values are provided during the installation of the Kubernetes plugin for the RoCE NIC. For more information about the parameters and their accepted values, `click here <../../../OmniaInstallGuide/Ubuntu/AdvancedConfigurationsUbuntu/k8s_plugin_roce_nic.html>`_.

**Resolution**: If the RoCE pod is in 'Pending' or 'ContainerCreating' state, describe the pod to check for issues. If there is a mistake in the parameter values provided, use ``delete_roce_plugin.yml`` to delete the configurations made for the Kubernetes RoCE plugin, append the ``input/roce_plugin_config.yml`` with correct values and re-deploy the RoCE pod by executing ``deploy_roce_plugin.yml``.