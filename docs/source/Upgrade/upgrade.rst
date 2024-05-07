Upgrade Omnia
==============

This playbook invokes the v1.6 ``omnia.yml`` tasks to setup the cluster in 1.6 format, that is, configuring scheduler, storage, security and telemetry.

To use the playbook, execute the following command: ::

    cd upgrade
    ansible-playbook upgrade.yml -i inventory

Where inventory refers to the auto-generated Omnia v1.6 inventory.

.. note::

    * Upgrade flow upgrades the existing omnia v1.5.1 cluster and should not be combined with provisioning of new nodes for Omnia v1.6.
    * Upgrade flow tries best to map v1.5.1 input configs to v1.6, but user has to review the same before running ``prepare_upgrade.yml``.
    * Addition of new nodes can be performed after Omnia upgrade by providing suitable parameters in v1.6 input configs like ``provision_config.yml``.
    * As part of upgrade, existing v1.5.1 features are migrated. The new Omnia v1.6 functionalities can be restricted depending on the way Omnia v1.5.1 was setup. For example, in Omnia v1.5.1 OpenLDAP client configuration was supported. If you had configured OpenLDAP client to external enterprise LDAP server in Omnia v1.5.1, then this configuration will not be restored during upgrade. In Omnia v1.6, Omnia installs OpenLDAP server and user you to reconfigure the OpenLDAP server to integrate it with an external LDAP server. Similarly, the slurm on Omnia v1.5.1 is upgraded to configless slurm in v1.6.