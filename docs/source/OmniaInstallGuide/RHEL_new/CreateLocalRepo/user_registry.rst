User registry
=================

User registry is an user-defined storehouse to store the software packages locally so that they can be accessed in an air-gapped environment, that is, without connecting to the public network.

.. note::

    * The ``user_registry`` path mentioned in the ``input/local_repo_config.yml`` supports only nerdctl and docker registries.
    * If you define the ``cert_path`` variable, ensure that it points to the absolute path of the user registry certificate present on the OIM.
    * To avoid docker pull limit issues, provide docker credentials (``docker_username`` and ``docker_password``) in the ``input/provision_config_credentials.yml`` file.

.. caution:: In order to download the software images from an user registry, you need to ensure that the ``user_registry`` path provided in ``input/local_repo_config.yml`` is accessible from the OIM. If the ``user_registry`` is not accessible from the OIM, all software images listed in the ``input/software_config.json`` gets downloaded to the Omnia-registry. Use the ``curl -k <user_registry>`` command to check if the registry is accessible or not.

Images listed in ``user_registry`` in ``input/local_repo_config.yml`` are accessed from user defined registries. To ensure that the OIM can correctly access the registry, ensure that the following naming convention is used to save the image: ::

    <host>/<image name>:v<version number>

Therefore, for the image of ``calico/cni`` version ``1.2`` available on ``quay.io`` that has been pulled to a local host: ``server1.omnia.test``, the accepted user registry name is: ::

    server1.omnia.test:5001/calico/cni:v1.2

Omnia will not be able to configure access to any registries that do not follow this naming convention. Do not include any other extraneous information in the registry name.

Instructions to pull images from the user registries in the form of a digest:

    * Images pulled from gcr.io (Google Container Registry) does not have a ``tag``, but a ``digest value``.

        *Details of an image pulled from gcr.io* ::

             {
                    "package": "gcr.io/knative-releases/knative.dev/serving/cmd/webhook",
                    "digest": "7b138c73fcaaf0b9bb2d414b8a89a780f8c09371d24c6f57969be1694acf4aaa",
                    "type": "image"
             },

    * While pushing these images to ``user_registry``, you need to delete the ``digest value`` and manually enter a ``tag`` with value set to ``omnia``. Tags make the image unique to Omnia ``user_registry``. If not provided, image will be accessed from the ``gcr.io`` registry, that is, from the internet. Follow the below

        *While pushing a software image to the user_registry, add "tag" value as "omnia" in the <software>.json file.* ::

            {
                    "package": "gcr.io/knative-releases/knative.dev/serving/cmd/webhook",
                    "tag": "omnia",
                    "type": "image"
            },

.. note::
   To enable a repository from your RHEL subscription, run the following commands: ::

            subscription-manager repos --enable=rhel-9-for-x86_64-appstream-rpms
            subscription-manager repos --enable=rhel-9-for-x86_64-baseos-rpms

Pull images from the ``user_registry`` or ``Omnia local registry``
----------------------------------------------------------------------

To fetch images from the ``user_registry`` or the Omnia local registry, run the below commands:

    * Images defined with versions: ``nerdctl pull <global_registry>/<image_name>:<tag>``
    * Images defined with digests: ``nerdctl pull <global_registry>/<image_name>:omnia``

.. note::

    * Images downloaded from ``gcr.io`` into the local ``user_registry`` are no longer accessible using digest values, but with the ``omnia`` tag. Choose one of the following methods when pushing these images to the cluster nodes:

       * Add ``omnia`` to the end of the image name while pushing images to the ``user_registry``. Update the image definition in ``input/config/<cluster_os_type>/<cluster_os_version>/<software>.json`` similarly.

       * If a different tag is provided, update the digest value in ``input/config/<cluster_os_type>/<cluster_os_version>/<software>.json`` as per the image digest in the ``user_registry``. To get the updated digest from the ``user_registry``, use the below steps:

            * Check the tag of an image: ``curl -k https://<user_registry>/v2/<image_name>/tags/list``

            * Check the digest value of the tag: ``curl -H <headers> -k https://<user_registry>/v2/<image_name>/manifests/omnia``