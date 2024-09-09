Upgrade Omnia
==============

This is the third step of upgrade process and uses the ``upgrade.yml`` playbook.

To execute the ``upgrade.yml`` playbook, run the following command: ::

    cd omnia/upgrade
    ansible-playbook upgrade.yml -i <omnia_1.6_inventory_filepath>

This is the final step, and once the ``upgrade.yml`` playbook is executed successfully, the upgrade process is complete!