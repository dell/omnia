Local Repositories
===================

⦾ **Why does running local_repo.yml fail with connectivity errors?**

**Potential Cause**: The control plane was unable to reach a required online resource due to a network glitch.

**Resolution**: Verify all connectivity and re-run the playbook.


⦾ **Why does any script that installs software fail with "The checksum for <software repository path> did not match."**?

**Potential Cause**: A local repository for the software was not configured by ``local_repo.yml``.

**Resolution**:

    * Delete the tarball/image/deb of the software from ``<repo_path>/cluster/tarball``.
    * Re-run ``local_repo.yml``.
    * Re-run the script to install the software.


⦾ **Why does the task `configure registry: Start and enable nerdctl-registry service` fail with "Job for nerdctl-registry.service failed because the control process exited with error code"?**

.. image:: ../../../images/nerdctlError.png

**Potential Causes**:

    * The subnet 10.4.0.0/24 has been assigned to the admin, bmc, or additional network. nerdctl uses this subnet by default and cannot be assigned to any other interface in the system.
    * The docker pull limit has been breached.

**Resolutions**:

    * Reassign the conflicting network to a different subnet.
    * Update ``input/provision_config_credentials.yml`` with the ``docker_username`` and ``docker_password``.