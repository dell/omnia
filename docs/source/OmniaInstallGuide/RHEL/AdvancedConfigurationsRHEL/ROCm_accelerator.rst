Alternate method to install the AMD ROCm platform
=====================================================

The accelerator role allows users to  set up the `AMD ROCm <https://rocm.docs.amd.com/projects/install-on-linux/en/latest/>`_ platform. This tools allow users to unlock the potential of installed AMD GPUs.

**Prerequisites**

* Ensure that the ROCm local repositories are configured using the `local_repo.yml <../CreateLocalRepo/index.html>`_ script.
* Ensure that the ``input/software_config.json`` contains valid amdgpu and rocm version. See `input parameters <../CreateLocalRepo/InputParameters.html>`_ for more information.

.. note::
	* Nodes provisioned using the Omnia provision tool do not require a RedHat subscription to run ``accelerator.yml`` on RHEL target nodes.
	* For RHEL target nodes not provisioned by Omnia, ensure that RedHat subscription is enabled on all target nodes. Every target node will require a RedHat subscription.
	* AMD ROCm driver installation is not supported by Omnia on Rocky Linux cluster nodes.

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

* To enable users to use rocm tools, use the following command as shown in the below added sample file: ::

        /opt/rocm/bin/<rocm command>

.. image:: ../../../images/ROCm_user_permissions.png

For any configuration changes, check out ROCm's official documentation `here. <https://rocm.docs.amd.com/projects/install-on-linux/en/latest/how-to/prerequisites.html>`_