Prepare Upgrade
================

This is the second step of upgrade process and uses the ``prepare_upgrade.yml`` playbook.

To execute the ``prepare_upgrade.yml`` playbook, run the following command: ::

    cd omnia/upgrade
    ansible-playbook prepare_upgrade.yml -i <Omnia_1.6_inventory_file_path>
