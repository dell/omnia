Alternate method to install the AMD ROCm platform
=====================================================

The accelerator role allows users to  set up the `AMD ROCm <https://rocm.docs.amd.com/projects/install-on-linux/en/latest/>`_ platform. This tools allow users to unlock the potential of installed AMD GPUs.

**Prerequisites**

* The ROCm local repositories must be configured using the `local_repo.yml <../CreateLocalRepo/index.html>`_ script.
* The ``input/software_config.json`` must contain valid ``amdgpu`` and ``rocm`` version. See `input parameters <../CreateLocalRepo/InputParameters.html>`_ for more information.

**Playbook configurations**

The following configurations takes place while running the ``accelerator.yml`` playbook:

	i. Servers with AMD GPUs are identified and the latest GPU drivers and ROCm platforms are downloaded and installed.
	ii. Servers with no GPU are skipped.

**Executing the playbook**

To install all the latest GPU drivers and toolkits, run: ::

	cd accelerator
	ansible-playbook accelerator.yml -i inventory

User permissions for ROCm platforms
------------------------------------

* To add an user to the ``render`` and ``video`` group, use the following command: ::

        sudo usermod -a -G render,video <user>

.. note::
        * <user> is the system name of the end user.
        * This command must be run with ``root`` permissions.
        * If the root user wants to provide access to other users and their individual GPU nodes, the previous command needs to be run on all of them separately.

* To enable users to use ROCm tools, use the following command as shown in the below added sample file: ::

        /opt/rocm/bin/<ROCm command>

.. image:: ../../../images/ROCm_user_permissions.png

For any configuration changes, check out ROCm's official documentation `here. <https://rocm.docs.amd.com/projects/install-on-linux/en/latest/how-to/prerequisites.html>`_