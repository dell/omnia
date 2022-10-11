Creating a New Cluster
=======================

From Omnia 1.2, the cobbler container OS will follow the OS on the control plane but will deploy multiple OS's based on the provision_os value in ``base_vars.yml``.


* When creating a new cluster, ensure that the iDRAC state is not PXE.

* On adding the cluster, run the iDRAC template before running control_plane.yml

* If the new cluster is to run on a different OS than the previous cluster, update the parameters provision_os and iso_file_path in base_vars.yml. Then run control_plane.yml

    | Example: In a scenario where the user wishes to deploy Red Hat and Rocky on their multiple servers, below are the steps they would use:
    |
    |
    | 1. Set ``provision_os`` to redhat and ``iso_file_path`` to /root/rhel-8.5-DVD-x86_64-Current.iso.
    |
    | 2. Run ``control_plane.yml`` to provision leap and create a profile called ``rhel-x86_64`` in the cobbler container.
    |
    | 3. Set ``provision_os`` to rocky and ``iso_file_path`` to /root/Rocky-8.x-x86_64-minimal.iso.
    |
    | 4. Run ``control_plane.yml`` to provision rocky and create a profile called rocky-x86_64 in the cobbler container.

.. note:: All compute nodes in a cluster must run the same OS.
