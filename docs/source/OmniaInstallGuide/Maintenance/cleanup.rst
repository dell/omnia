Uninstalling the OIM tools
------------------------------

Run this script to roll back all modifications made to the OIM, such as configured local repositories, provisioning tools, and telemetry configurations.

To run the script: ::

    cd utils
    ansible-playbook oim_cleanup.yml

To skip the deletion of the configured local repositories (stored in ``repo_store_path`` and xCAT repositories), run: ::

    ansible-playbook oim_cleanup.yml –-skip-tags downloads

To delete the changes made by ``local_repo.yml`` while retaining the ``repo_store_path`` folder, run: ::

    ansible-playbook oim_cleanup.yml -–tags local_repo  --skip-tags downloads

To delete the changes made by ``local_repo.yml`` including the ``repo_store_path`` folder, run: ::

   	ansible-playbook oim_cleanup.yml –-tags local_repo


.. note:: After you run the ``oim_cleanup.yml`` playbook, ensure to reboot the OIM node.

.. caution::
    * When re-provisioning your cluster (that is, re-running the ``discovery_provision.yml`` playbook) after a clean-up, ensure to use a different ``admin_nic_subnet`` in ``input/provision_config.yml`` to avoid a conflict with newly assigned servers. Alternatively, disable any OS available in the ``Boot Option Enable/Disable`` section of your BIOS settings (``BIOS Settings`` > ``Boot Settings`` > ``UEFI Boot Settings``) on all target nodes.
    * On subsequent runs of ``discovery_provision.yml``, if users are unable to log into the server, refresh the ssh key manually and retry. ::

        ssh-keygen -R <node IP>

