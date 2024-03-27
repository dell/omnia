Before you create local repositories
-------------------------------------

**Space considerations**

If all available software stacks are configured, the free space required on the control plane is as below:

    * For packages: 30GB
    * For images (in ``/var``): 400GB
    * For storing repositories (the file path should be specified in ``repo_store_path`` in ``input/local_repo_config.yml``): 30GB.

**On Ubuntu clusters**

For persistent offline local repositories, (If the parameter ``repo_config`` in ``input/software_config`` is set to ``always``), click `here <https://help.ubuntu.com/community/Debmirror>`_ to set up the required repositories.

.. note:: This link explains how to build a mirror on an Ubuntu 20.04 server. Adapt the steps and scripts as required for any other version of Ubuntu.

**When creating user registries**

To avoid docker pull limits, provide docker credentials (``docker_username``, ``docker_password``) in ``input/provision_config_credentials.yml``.

Images listed in ``user_registry`` in ``input/local_repo_config.yml`` are accessed from user defined registries. To ensure that the control plane can correctly access the registry, ensure that the following naming convention is used to save the image: ::

    <host>/<image name>:v<version number>

Therefore, for the image of ``calico/cni`` version ``1.2`` available on ``quay.io`` that has been pulled to a local host: ``server1.omnia.test``, the accepted user registry name is: ::

    server1.omnia.test:5001/calico/cni:v1.2

Omnia will not be able to configure access to any registries that do not follow this naming convention. Do not include any other extraneous information in the registry name.

There are two ways to pull images from the user registries in the form of a digest:

    * Update the digest value to the listed image in the registry. All images to be pulled are listed in ``input/config/<os>/<version>/<software_file>.json``. A sample of the listing is shown below: ::

        {
            "package": "gcr.io/knative-releases/knative.dev/serving/cmd/webhook",
            "digest": ".1305209ce498caf783f39c8f3e85df..35ece6947033bf50b0b627983fd65953",
            "type": "image"

        },


    * While pushing the image to the user registry, create a tag and update the JSON file to take the tag value instead of the digest.