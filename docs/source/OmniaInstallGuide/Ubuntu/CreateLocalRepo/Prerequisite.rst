Prerequisites
===============

1. Set the hostname of the control plane in the "hostname.domain name" format.

.. include:: ../../../Appendices/hostnamereqs.rst

For example, ``controlplane.omnia.test`` is acceptable. ::

    hostnamectl set-hostname controlplane.omnia.test

2. To set up persistent offline local repositories, (if the parameter ``repo_config`` in ``input/software_config.json`` is set to ``always``), `click here <https://help.ubuntu.com/community/Debmirror>`_.

.. note:: The above link explains how to build a mirror on an Ubuntu 20.04 server. Adapt the steps and scripts as required for other versions of Ubuntu OS.

3. Creating user registries

.. note::

    * The ``user_registry`` in ``input/local_repo_config.yml`` supports only nerdctl and docker registries.
    * If you define the ``cert_path`` variable, ensure that it points to the absolute path of the user registry certificate present on the Omnia control plane.
    * To avoid docker pull limits, provide docker credentials (``docker_username``, ``docker_password``) in ``input/provision_config_credentials.yml``.

.. caution:: In order to download the software images from an user registry, the user needs to ensure that the ``user_registry`` address provided in ``input/local_repo_config.yml`` is accessible from the Omnia control plane. If the ``user_registry`` is not accessible from the control plane, Omnia will download all the software images listed in ``input/software_config.json`` to the Omnia-registry. Use the ``curl -k <user_registry>`` to check.

Images listed in ``user_registry`` in ``input/local_repo_config.yml`` are accessed from user defined registries. To ensure that the control plane can correctly access the registry, ensure that the following naming convention is used to save the image: ::

    <host>/<image name>:v<version number>

Therefore, for the image of ``calico/cni`` version ``1.2`` available on ``quay.io`` that has been pulled to a local host: ``server1.omnia.test``, the accepted user registry name is: ::

    server1.omnia.test:5001/calico/cni:v1.2

Omnia will not be able to configure access to any registries that do not follow this naming convention. Do not include any other extraneous information in the registry name.

Instructions to pull images from the user registries in the form of a digest:

    * Images pulled from gcr.io does not have a ``tag``, but a ``digest value``.

        *Image pulled from gcr.io* ::

             {
                    "package": "gcr.io/knative-releases/knative.dev/serving/cmd/webhook",
                    "digest": "7b138c73fcaaf0b9bb2d414b8a89a780f8c09371d24c6f57969be1694acf4aaa",
                    "type": "image"
             },

    * While pushing these images to ``user_registry``, user needs to manually enter a ``tag`` as shown in the sample below. Tags make the image unique to Omnia ``user_registry``. If not provided, image will be accessed from the ``gcr.io`` registry, that is, from the internet.

        *Add "tag" value as "omnia" in <software>.json file while pushing the image to user_registry* ::

            {
                    "package": "gcr.io/knative-releases/knative.dev/serving/cmd/webhook",
                    "tag": "omnia",
                    "type": "image"
            },

    * For "kserve" and "kubeflow" images sourced from ``gcr.io``, Omnia updates the digest tag to ``omnia-kserve`` and ``omnia-kubeflow`` while pushing the images to ``user_registry``.

