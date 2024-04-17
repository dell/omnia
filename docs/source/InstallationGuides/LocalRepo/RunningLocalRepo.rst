Running local repo
------------------

The local repository feature will help create offline repositories on the control plane which all the cluster nodes will access.

**Configurations made by the playbook**

    * A registry is created on the control plane at <Control Plane hostname>:5001.

    * If ``repo_config`` in ``local_repo_config.yml`` is set to ``always`` or ``partial``, all images present in the ``input/config/<operating system>/<version>`` folder will be downloaded to the control plane.


        * If the image is defined using a tag, the image will be tagged using <control plane hostname>:5001/<image_name>:<version> and pushed to the Omnia local registry.

        * If the image is defined using a digest, the image will be tagged using <control plane hostname>:5001/<image_name>:omnia and pushed to the Omnia local registry.repositories


    * When  ``repo_config`` in ``local_repo_config.yml`` is set to ``always``, the control plane is set as the default registry mirror.

    * When ``repo_config`` in ``local_repo_config`` is set to ``partial``, the ``user_registry`` (if defined) and the control plane are set as default registry mirrors.

To create local repositories, run the following commands: ::

    cd local_repo
    ansible-playbook local_repo.yml

.. caution:: During the execution of ``local_repo.yml``, Omnia 1.6 will remove packages such as ``podman``, ``containers-common``, and ``buildah`` (if they are already installed), as they conflict with the installation of ``containerd.io`` on RHEL/Rocky OS control plane.

Verify changes made by the playbook by running ``cat /etc/containerd/certs.d/_default/hosts.toml`` on compute nodes.

.. note::
    * View the status of packages for the current run of ``local_repo.yml`` in ``/opt/omnia/offline/download_package_status.csv``.
    * If any software packages failed to download during the execution of this script, scripts that rely on the package for their working (that is, scripts that install the software)  may fail.

To fetch images from the ``user_registry`` or the Omnia local registry, run the below commands:

    * Images defined with versions: ``nerdctl pull <global_registry>/<image_name>:<tag>``
    * Images defined with digests: ``nerdctl pull <global_registry>/<image_name>:omnia``

.. note::


    * After ``local_repo.yml`` has run, the value of ``repo_config`` in ``input/software_config.json`` cannot be updated without running the `control_plane_cleanup.yml <../CleanUpScript.html>`_ script first.

    * To configure additional local repositories after running ``local_repo.yml``, update ``software_config.json`` and re-run ``local_repo.yml``.

    * For images coming from ``gcr.io``, digests are defined as tags are not available. Omnia gives a custom tag of ‘omnia’ to these images. If such images need to be taken from the ``user_registry``, use one of the below steps:

        * Append 'omnia' to the end of the image name while pushing images to the ``user_registry``. Update the image definition in ``input/config/<operating system>/<version>/<software>.json`` to follow the same nomenclature.

        * If a different tag is provided, update the digest value in ``input/config/<operating system>/<version>/<software>.json`` as per the image digest in the ``user_directory``. To get the updated digest from the ``user_registry``, use the below steps:

            * Check the tag of image: ``curl -k https://<user_registry>/v2/<image_name>/tags/list``

            * Check the digest of the tag: ``curl -H <headers> -k https://<user_registry>/v2/<image_name>/manifests/omnia``


**Update local repositories**

This playbook updates all local repositories configured on a provisioned cluster after local repositories have been configured.

To run the playbook: ::

    cd utils
    ansible-playbook update_user_repo.yml -i inventory

