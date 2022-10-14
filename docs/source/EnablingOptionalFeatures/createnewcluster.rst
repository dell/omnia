Creating a New Cluster
=======================

If the new cluster is to run on a different OS than the previous cluster, update the parameters ``provision_os`` and ``iso_file_path`` in ``provision_config.yml``. Then run ``provision.yml``



    Example: In a scenario where the user wishes to deploy RHEL and Rocky on their multiple servers, below are the steps they would use:

        1. Set ``provision_os`` to ``rhel`` and ``iso_file_path`` to ``/root/rhel-8.x-DVD-x86_64-Current.iso``.

        2. Run ``provision.yml`` to create a rhel osimage.

        3. Set ``provision_os`` to ``rocky`` and ``iso_file_path`` to ``/root/Rocky-8.x-x86_64-minimal.iso``.

        4. Run ``provision.yml`` to create rocky osimage.

.. note:: All compute nodes in a cluster must run the same OS.
