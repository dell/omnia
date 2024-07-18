Upgrade
========

⦾ **Why does omnia.yml (or upgrade.yml, in case of upgrade) fail with an error “Unable to retrieve file contents. Could not find or access... kubernetes_sigs.kubespray.cluster on the Ansible Controller”?**

.. image:: ../../../images/kubernetes_unable_to_retrieve1.png

**Potential Cause**: This issue may arise when the task *‘prepare_cp/roles/omnia_appliance_cp: Install Kubespray ansible-collection’* in ``prepare_upgrade.yml`` silently passes (as shown in the following image), without installing the Kubespray ansible-collection. This can happen due to unstable internet connectivity on control plane during installation.

.. image:: ../../../images/kubernetes_unable_to_retrieve2.png

**Resolution**: Manually try to install the Kubespray ansible-collection as shown below and re-run the ``omnia.yml`` playbook (or ``upgrade.yml`` playbook in case of upgrade):

.. image:: ../../../images/kubernetes_unable_to_retrieve3.png


⦾ **While upgrading Omnia in an NFS-Bolt-On setup, the prepare_config.yml playbook fails to import the nfs_client_params mentioned in input/storage_config.yml for v1.5.1 to Omnia v1.6. Consequently, if the same NFS-Bolt-On share doubles as the Omnia share, the prepare_upgrade.yml playbook fails to unmount it on the head node.**

**Potential Cause**: This issue occurs when ``client_share_path`` or ``client_mount_options`` in ``nfs_client_params`` is left empty.

**Resolution**: Perform the following steps based on your cluster configuration:

    After executing the ``prepare_config.yml`` playbook, you need to manually update the ``nfs_client_params`` in ``input/storage_config.yml`` of Omnia v1.6, in the format `mentioned here <../InstallationGuides/BuildingClusters/NFS.html>`_. Ensure that the values for ``server_ip``, ``server_share_path``, ``client_share_path``, and ``client_mount_options`` are the same between Omnia v1.5.1 and v1.6.

	* When ``enable_omnia_nfs`` is set to ``true`` in Omnia v1.5.1, update the ``nfs_client_params`` in the format added below

            # For example, if ``nfs_client_params`` in Omnia v1.5.1 is: ::

                - { server_ip: 10.6.0.4, server_share_path: "/mnt/nfs_shares/users1", client_share_path: “/users1”, client_mount_options: }
                - { server_ip: 10.6.0.4, server_share_path: "/mnt/nfs_shares/users1", client_share_path: “/users2”, client_mount_options: }

            # Then the ``nfs_client_params`` in Omnia v1.6 should be updated as: ::

                - { server_ip: 10.6.0.4, server_share_path: "/mnt/nfs_shares/users1", client_share_path: “/users1”, client_mount_options: , nfs_server: false, slurm_share: false, k8s_share: false }
                - { server_ip: 10.6.0.4, server_share_path: "/mnt/nfs_shares/users1", client_share_path: “/users2”, client_mount_options: , nfs_server: false, slurm_share: false, k8s_share: false }

            .. note:: Do not remove the auto populated entries in ``nfs_client_params`` from ``input/storage_config.yml``. The default entry is similar to:
                ::
                    { server_ip: localhost, server_share_path: /mnt/omnia_home_share, client_share_path: /home, client_mount_options: "nosuid,rw,sync,hard,intr", nfs_server: true, slurm_share: true, k8s_share: true }

	* When ``enable_omnia_nfs`` is set to ``false`` and ``omnia_usrhome_share`` is set to ``/mnt/nfs_shares/appshare`` in Omnia v1.5.1,  update the ``nfs_client_params`` in the format added below

            # For example, if the ``nfs_client_params`` in Omnia v1.5.1 is: ::

                            { server_ip: 10.6.0.4, server_share_path: "/mnt/nfs_shares/users", client_share_path: , client_mount_options: }
                            { server_ip: 10.6.0.4, server_share_path: "/mnt/nfs_shares/appshare", client_share_path: , client_mount_options: }

            # Then the ``nfs_client_params`` in Omnia v1.6 should be updated as: ::

                            { server_ip: 10.6.0.4, server_share_path: "/mnt/nfs_shares/users", client_share_path: , client_mount_options: , nfs_server: false, slurm_share: false, k8s_share: false }
                            { server_ip: 10.6.0.4, server_share_path: "/mnt/nfs_shares/appshare", client_share_path: "/home", client_mount_options: , nfs_server: false, slurm_share: true, k8s_share: true }

    .. note:: When ``enable_omnia_nfs`` is set to ``false``, the ``prepare_upgrade.yml`` playbook execution fails while attempting to delete the nfs_share directory from the manager node. In such a scenario, the user needs to manually unmount the Omnia NFS share from the head node and re-run the ``prepare_upgrade.yml`` playbook.