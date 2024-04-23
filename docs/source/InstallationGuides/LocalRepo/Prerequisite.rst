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

    * Images pulled from gcr.io does not have a ``tag``, but a ``digest value``. While pushing these images to ``user_registry``, user needs to manually enter a ``tag`` as shown in the sample below. Tags make the image unique to Omnia ``user_registry``. If not provided, image will be accessed from the ``gcr.io`` registry, that is, from the internet.
    * While pushing the image to the user registry, create a tag and update the JSON file to take the tag value instead of the digest.


.. note::
   * Enable a repository from your RHEL subscription, run the following commands: ::

            subscription-manager repos --enable=rhel-8-for-x86_64-appstream-rpms
            subscription-manager repos --enable=rhel-8-for-x86_64-baseos-rpms

    * Enable an offline repository by creating a ``.repo`` file in ``/etc/yum.repos.d/``. Refer the below sample content: ::

                [RHEL-8-appstream]

                name=Red Hat AppStream repo

                baseurl=http://xx.yy.zz/pub/Distros/RedHat/RHEL8/8.6/AppStream/x86_64/os/

                enabled=1

                gpgcheck=0

                [RHEL-8-baseos]

                name=Red Hat BaseOS repo

                baseurl=http://xx.yy.zz/pub/Distros/RedHat/RHEL8/8.6/BaseOS/x86_64/os/

                enabled=1

                gpgcheck=0



    * Verify your changes by running: ::

            yum repolist enabled
            Updating Subscription Management repositories.
            Unable to read consumer identity
            This system is not registered with an entitlement server. You can use subscription-manager to register.
                repo id                                                           repo name
                RHEL-8-appstream-partners                                         Red Hat Enterprise Linux 8.6.0 Partners (AppStream)
                RHEL-8-baseos-partners                                            Red Hat Enterprise Linux 8.6.0 Partners (BaseOS)


