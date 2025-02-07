Execute local repo playbook
=============================

The local repository feature helps create offline repositories on the OIM, which all the cluster nodes can access.

**Configurations made by the playbook**

    * A registry is created on the OIM at <OIM hostname>:5001.

    * If ``repo_config`` in ``input/software_config.json`` is set to ``always`` or ``partial``, all images present in the ``input/config/<cluster_os_type>/<cluster_os_version>`` folder will be downloaded to the OIM.


        * If the image is defined using a tag, the image will be tagged using <OIM hostname>:5001/<image_name>:<version> and pushed to the Omnia local registry.

        * If the image is defined using a digest, the image will be tagged using <OIM hostname>:5001/<image_name>:omnia and pushed to the Omnia local registry.repositories


    * When  ``repo_config`` in ``input/software_config.json`` is set to ``always``, the OIM is set as the default registry mirror.

    * When ``repo_config`` in ``input/software_config.json`` is set to ``partial``, the ``user_registry`` (if defined) and the OIM are set as default registry mirrors.

**Create & Verify local repo**

* To create local repositories, execute the following command: ::

    cd local_repo
    ansible-playbook local_repo.yml

.. caution:: During the execution of ``local_repo.yml``, Omnia 1.7 will remove packages such as ``podman``, ``containers-common``, and ``buildah`` (if they are already installed), as they conflict with the installation of ``containerd.io`` on RHEL/Rocky Linux OS OIM.

* Verify changes made by the playbook by running ``cat /etc/containerd/certs.d/_default/hosts.toml`` on compute nodes.

.. note::
    * View the status of packages for the current run of ``local_repo.yml`` in ``/opt/omnia/offline/download_package_status.csv``. Packages which are already a part of AppStream or BaseOS repositories show up as ``Skipped``.
    * ``local_repo.yml`` playbook execution fails if any software package download fails. Packages that fail are marked with a "Failed" status. In such a scenario, the user needs to re-run the ``local_repo.yml`` playbook. For more information, `click here <../../../Troubleshooting/FAQ/Common/LocalRepo.html>`_.
    * If ``repo_config`` is set to ``partial``, packages which are part of the ``user_repo_url`` or images which are part of ``user_registry`` have a ``Skipped`` status in ``/opt/omnia/offline/download_package_status.csv``.
    * If any software packages failed to download during the execution of this script, scripts that rely on the package for their working (that is, scripts that install the software)  may fail.

To fetch images from the ``user_registry`` or the Omnia local registry, run the below commands:

    * Images defined with versions: ``nerdctl pull <global_registry>/<image_name>:<tag>``
    * Images defined with digests: ``nerdctl pull <global_registry>/<image_name>:omnia``

.. note::


    * After ``local_repo.yml`` has run, the value of ``repo_config`` in ``input/software_config.json`` cannot be updated without running the `oim_cleanup.yml <../../Maintenance/cleanup.html>`_ playbook first.

    * To configure additional local repositories after running ``local_repo.yml``, update ``software_config.json`` and re-run ``local_repo.yml``.

    * Images downloaded from ``gcr.io`` into the local registry are no longer accessible using digest values. These images are tagged with the 'omnia' tag. Choose one of the following methods when pushing these images to the cluster nodes:

        * Append 'omnia' to the end of the image name while pushing images to the ``user_registry``. Update the image definition in ``input/config/<cluster_os_type>/<cluster_os_version>/<software>.json`` to follow the same nomenclature.

        * For "kserve" and "kubeflow" images sourced from ``gcr.io``, Omnia updates the digest tag to ``omnia-kserve`` and ``omnia-kubeflow`` while pushing the images to ``user_registry``.

        * If a different tag is provided, update the digest value in ``input/config/<cluster_os_type>/<cluster_os_version>/<software>.json`` as per the image digest in the ``user_directory``. To get the updated digest from the ``user_registry``, use the below steps:

            * Check the tag of image: ``curl -k https://<user_registry>/v2/<image_name>/tags/list``

            * Check the digest of the tag: ``curl -H <headers> -k https://<user_registry>/v2/<image_name>/manifests/omnia``


**Update local repositories**

This playbook updates all local repositories configured on a provisioned cluster after local repositories have been configured.

To run the playbook: ::

    cd utils
    ansible-playbook update_user_repo.yml -i inventory
