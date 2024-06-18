Upgrade Omnia v1.5.1 to v1.6
=============================

The upgrade feature in v1.6 helps customers to upgrade their Omnia setup from v1.5.1 to v1.6. This includes upgrading the essential software requirements, configurations, and cluster software.

**Prerequisites**

    1. The control plane must have internet connectivity and run a full version of the operating system.

    2. If Git is not installed on the control plane, install Git using the following command: ::

           dnf install git -y

    3. Clone the Omnia v1.6 repository from GitHub and place it in a directory on the control plane. This directory must be different from the one containing the Omnia v1.5.1 repository. Execute the following command to perform the cloning operation: ::

           git clone https://github.com/dell/omnia.git

Once the cloning process is done, follow the steps listed below to invoke the upgrade process:

.. toctree::

    prepare_config
    prepare_upgrade
    upgrade

.. note::

    * Upgrade flow tries best to map v1.5.1 input configurations to v1.6, but the user must review the same before running ``prepare_upgrade.yml``.
    * Upgrade flow upgrades the existing Omnia v1.5.1 cluster and should not be combined with provisioning of new nodes for Omnia v1.6.
    * Addition of new nodes can be performed after Omnia upgrade by providing suitable parameters in v1.6 input configurations files such as ``provision_config.yml``.
    * Upgrade flow resets the existing kubernetes setup on the cluster and updates other relevant software as well. Hence, ensure there are no active jobs running on the cluster when the upgrade is planned.
    * Omnia v1.6 upgrade feature disables the NFS server on the head node and configures it on the control plane. The NFS share directory mentioned in ``omnia_usrhome_share``, provided in v1.5.1 ``omnia_config.yml``, is unmounted from the cluster and deleted from the head node while executing the ``prepare_upgrade.yml`` playbook. Hence, ensure the cluster does not have any Kubernetes jobs or any other active jobs running when the upgrade is planned.
    * As part of upgrade, existing v1.5.1 features are migrated. The new Omnia v1.6 functionalities can be restricted depending on the way Omnia v1.5.1 was setup. For example:

        - In Omnia v1.5.1 OpenLDAP client configuration was supported. If you had configured OpenLDAP client to external enterprise LDAP server in Omnia v1.5.1, then this configuration will not be restored during upgrade. In Omnia v1.6, Omnia installs OpenLDAP server and the user needs to reconfigure the OpenLDAP server to integrate it with an external LDAP server.
        - The slurm setup in Omnia v1.5.1 cluster is upgraded to configless slurm in v1.6.
    * While the Omnia upgrade process does attempt an automatic backup of the Telemetry database, it is recommended to manually create a backup before initiating the upgrade for added precaution. After the upgrade, the restoration of the telemetry database must be performed manually by the user.

        * Omnia recommends to stop the telemetry services in Omnia v1.5.1 by configuring ``idrac_telemetry_support`` and ``omnia_telemetry_support`` to ``false`` in ``input/telemetry_config.yml``, followed by the execution of the ``telemetry.yml`` playbook before proceeding with the upgrade flow.
        * For a successful restoration of the telemetry database in Omnia v1.6, ensure ``input/telemetry_config.yml`` has ``idrac_telemetry_support`` set to ``false`` and ``omnia_telemetry_support`` set to ``true``, after executing ``prepare_config.yml``.

.. caution:: The NFS share directory mentioned in ``omnia_usrhome_share``, provided in v1.5.1 ``omnia_config.yml``, is unmounted from the cluster and deleted from the head node, along with all the user data while executing the ``prepare_upgrade.yml`` playbook. Hence, it is recommended that you take a backup of the Omnia NFS share before executing the ``prepare_upgrade.yml`` playbook.