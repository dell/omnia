Extra Packages for Enterprise Linux (EPEL)
===========================================

This script is used to install the following packages:

    1. `PDSH <https://linux.die.net/man/1/pdsh>`_
    2. `PDSH RCMD SSH <https://linux.die.net/man/1/pdsh>`_
    3. `clustershell <https://clustershell.readthedocs.io/en/latest/>`_

To run the script: ::

    cd omnia/utils
    ansible-playbook install_hpc_thirdparty_packages.yml -i inventory

Where the inventory refers to a file listing all manager and compute nodes per the format provided in `inventory file <../samplefiles.html>`_.

