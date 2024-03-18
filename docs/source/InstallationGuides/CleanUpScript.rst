Uninstalling the provision tool
--------------------------------

Use this script to undo all the changes made by the provision tool. For a list of actions taken by the provision tool, `click here <https://omnia-doc.readthedocs.io/en/latest/InstallationGuides/InstallingProvisionTool/installprovisiontool.html>`_ .

To run the script: ::

    cd utils
    ansible-playbook control_plane_cleanup.yml

To skip the deletion of the configured local repositories (stored in ``repo_store_path`` and xCAT repositories), run: ::

    ansible-playbook control_plane_cleanup.yml –skip-tags downloads

To delete the changes made by ``local_repo.yml`` while retaining the ``repo_store_path`` folder, run: ::

    ansible-playbook control_plane_cleanup.yml –tags local_repo  --skip-tags downloads

To delete the changes made by ``local_repo.yml`` including the ``repo_store_path`` folder, run: ::

   	ansible-playbook control_plane_cleanup.yml –tags local_repo


.. caution::
    * When re-provisioning your cluster (that is, re-running the ``provision.yml`` playbook) after a clean-up, ensure to use a different ``admin_nic_subnet`` in ``input/provision_config.yml`` to avoid a conflict with newly assigned servers. Alternatively, disable any OS available in the ``Boot Option Enable/Disable`` section of your BIOS settings (``BIOS Settings`` > ``Boot Settings`` > ``UEFI Boot Settings``) on all target nodes.
    * On subsequent runs of ``provision.yml``, if users are unable to log into the server, refresh the ssh key manually and retry. ::

        ssh-keygen -R <node IP>

