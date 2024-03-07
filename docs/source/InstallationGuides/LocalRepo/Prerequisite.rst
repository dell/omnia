Before you create local repositories
-------------------------------------

**On Ubuntu clusters**

For persistent offline local repositories, (If the parameter ``repo_config`` in ``input/software_config`` is set to ``always``), click `here <https://help.ubuntu.com/community/Debmirror>`_ to set up the required repositories.

.. note:: This link explains how to build a mirror on an Ubuntu 20.04 server. Adapt the steps and scripts as required for any other version of Ubuntu.

**When creating user registries**

If ``repo_config`` in ``input/software_config.json`` is set to ``partial`` or ``never``, images listed in ``user_registry`` in ``input/local_repo_config.yml`` are accessed from user defined registries. To ensure that the control plane can correctly access the registry, ensure that the following naming convention is used to save the image: ::

    <host>/<image name>:v<version number>

Therefore, for the image of calico/cni version 1.2 available on quay.io that has been pulled to a local host server1.omnia.test, the accepted user registry name is: ::

    server1.omnia.test:5001/calico/cni:v1.2

Omnia will not be able to configure access to any registries that do not follow this naming convention. Do not include any other extraneous information in the registry name.