Upgrade Omnia
==============

This playbook invokes the v1.6 ``omnia.yml`` tasks to setup the cluster in 1.6 format, that is, configuring scheduler, storage, security and telemetry.

To use the playbook, execute the following command: ::

    ansible-playbook upgrade.yml -i inventory

.. note::

    * Upgrade flow upgrades the existing omnia v1.5.1 cluster and should not be combined with provisioning of new nodes for Omnia v1.6.
    * Upgrade flow tries best to map v1.5.1 input configs to v1.6, but user has to review the same before running ``prepare_upgrade.yml``.
    * Addition of new nodes can be performed after Omnia upgrade by providing suitable parameters in v1.6 input configs like ``provision_config.yml``.
    * As part of upgrade, existing v1.5.1 features are migrated. The new Omnia v1.6 functionalities can be unlocked/locked depending the on existing setup. For example, openLDAP configuration in omnia v1.5.1 and in omnia v1.6 is entirely different and hence full end-to-end openLDAP upgrade wont be handled as part of the Omnia upgrade process.
