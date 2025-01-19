Provision
===========

⦾ **Why does the provisioning status of Ubuntu remote servers remain stuck at ‘bmcready’ or 'powering-on' in cluster.nodeinfo (omniadb)?**

.. image:: ../../../images/ubuntu_pxe_failure.png

.. csv-table::
   :file: ../../../Tables/FAQ_provision.csv
   :header-rows: 1
   :keepspace:

⦾ **Why does the provisioning status of Kubernetes RoCE pod remain stuck at 'Pending' or 'ContainerCreating' state?**

**Potential Cause**: This issue is encountered if incorrect parameter values are provided during the installation of the Kubernetes plugin for the RoCE NIC. For more information about the parameters and their accepted values, `click here <../../../OmniaInstallGuide/Ubuntu/AdvancedConfigurationsUbuntu/k8s_plugin_roce_nic.html>`_.

**Resolution**: If the RoCE pod is in 'Pending' or 'ContainerCreating' state, describe the pod to check for issues. If there is a mistake in the parameter values provided, use ``delete_roce_plugin.yml`` to delete the configurations made for the Kubernetes RoCE plugin, append the ``input/roce_plugin_config.yml`` with correct values and re-deploy the RoCE pod by executing ``deploy_roce_plugin.yml``.

⦾ **Why does the node get stuck in "standby" status and continuously PXE boots during the installation of AMD ROCm drivers in the cluster provisioning process?**

**Potential Cause**: This can happen due to any hardware or firmware issues on the node.

**Resolution**: Resolve the underlying hardware or firmware issues and re-run the ``discovery_provision.yml`` playbook.