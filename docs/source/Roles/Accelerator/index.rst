GPU accelerator configuration
-------------------------------

The accelerator role allows users to  set up the `AMD ROCm <https://rocm.docs.amd.com/projects/install-on-linux/en/latest/>`_ platform or the `CUDA Nvidia toolkit <https://developer.nvidia.com/cuda-zone>`_. These tools allow users to unlock the potential of installed GPUs.

Ensure that CUDA and ROCm local repositories are configured using the `local_repo.yml script. <../../InstallationGuides/LocalRepo/index.html>`_

Enter all required parameters in ``input/accelerator_config.yml``.

+----------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Parameters           | Details                                                                                                                                                                                                                                                                                                                                                                                                                                 |
+======================+=========================================================================================================================================================================================================================================================================================================================================================================================================================================+
| cuda_toolkit_version | Required CUDA toolkit version.  By   default latest cuda is installed unless cuda_toolkit_path is specified.  Default: latest (11.8.0).                                                                                                                                                                                                                                                                                                 |
|      ``string``      |                                                                                                                                                                                                                                                                                                                                                                                                                                         |
|      Optional        |      **Default values**: ``latest``                                                                                                                                                                                                                                                                                                                                                                                                     |
+----------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| cuda_toolkit_path    | If the latest cuda toolkit is not required, provide an offline copy of   the toolkit installer in the path specified. (Take an RPM copy of the toolkit   from `here <https://developer.nvidia.com/cuda-downloads>`_).  If ``cuda_toolkit_version``  is not latest, giving   ``cuda_toolkit_path``  is mandatory.                                                                                                                        |
|      ``string``      |                                                                                                                                                                                                                                                                                                                                                                                                                                         |
|      Optional        |                                                                                                                                                                                                                                                                                                                                                                                                                                         |
+----------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| cuda_stream          | A stream in CUDA is a sequence of operations that execute on the device   in the order in which they are issued by the host code.                                                                                                                                                                                                                                                                                                       |
|    ``string``        |                                                                                                                                                                                                                                                                                                                                                                                                                                         |
|     Optional         |      **Default values**: ``latest-dkms``                                                                                                                                                                                                                                                                                                                                                                                                |
+----------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+


.. note::
	* Nodes provisioned using the Omnia provision tool do not require a RedHat subscription to run ``accelerator.yml`` on RHEL target nodes.
	* For RHEL target nodes not provisioned by Omnia, ensure that RedHat subscription is enabled on all target nodes. Every target node will require a RedHat subscription.
	* AMD ROCm driver installation is not supported by Omnia on Rocky Linux cluster  nodes.

To install all the latest GPU drivers and toolkits, run: ::

	cd accelerator
	ansible-playbook accelerator.yml -i inventory


The following configurations take place when running ``accelerator.yml``

	i. Servers with AMD GPUs are identified and the latest GPU drivers and ROCm platforms are downloaded and installed.
	ii. Servers with NVIDIA GPUs are identified and the specified CUDA toolkit is downloaded and installed.
	iii. For the rare servers with both NVIDIA and AMD GPUs installed, all the above mentioned download-ables are installed to the server.
	iv. Servers with neither GPU are skipped.

User permissions for ROCm platforms
------------------------------------

* To add an user to the ``render`` and ``video`` group, use the following command: ::

        sudo usermod -a -G render,video <user>

.. note::
        * <user> is the system name of the end user.
        * This command must be run with ``root`` permissions.
        * If the root user wants to provide access to other users and their individual GPU nodes, the previous command needs to be run on all of them separately. ::

* To enable users to use rocm tools, use the following command as shown in the below added sample file: ::

        /opt/rocm/bin/<rocm command>

.. image:: ../../images/ROCm_user_permissions.png

For any configuration changes, check out ROCm's official documentation `here. <https://rocm.docs.amd.com/projects/install-on-linux/en/latest/how-to/prerequisites.html>`_