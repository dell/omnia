Upgrade Omnia
==============

This is the third step of upgrade process and uses the ``upgrade.yml`` playbook. This playbook performs the following task:

    * Invokes the v1.6 ``omnia.yml`` tasks to setup the cluster in 1.6 format, that is, configuring scheduler, storage, security and telemetry.

To execute the ``upgrade.yml`` playbook, run the following command: ::

    cd omnia/upgrade
    ansible-playbook upgrade.yml -i inventory

Where inventory refers to the auto-generated inventory file in Omnia v1.6 format.

This is the final step, and once the upgrade.yml playbook is executed successfully, the upgrade process is complete!