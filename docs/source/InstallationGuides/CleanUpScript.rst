Uninstalling the provision tool
--------------------------------

Use this script to undo all the changes made by the provision tool. For a list of actions taken by the provision tool, `click here <https://omnia-doc.readthedocs.io/en/latest/InstallationGuides/InstallingProvisionTool/installprovisiontool.html>`_ .

To run the script: ::

    cd utils
    ansible-playbook control_plane_cleanup.yml

.. caution::
    * When re-provisioning your cluster (that is, re-running the ``provision.yml`` playbook) after a clean-up, ensure to use a different ``admin_nic_subnet`` in ``input/provision_config.yml`` to avoid a conflict with newly assigned servers. Alternatively, disable any OS available in the ``Boot Option Enable/Disable`` section of your BIOS settings (``BIOS Settings`` > ``Boot Settings`` > ``UEFI Boot Settings``) on all target nodes.
    * On subsequent runs of ``provision.yml``, if users are unable to log into the server, refresh the ssh key manually and retry. ::

        ssh-keygen -R <node IP>

