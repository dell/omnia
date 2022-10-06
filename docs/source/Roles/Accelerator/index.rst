Accelerator
============

The accelerator role allows users to  set up the AMD ROCm platform or the CUDA Nvidia toolkit. These tools allow users to unlock the potential of installed GPUs.

Enter all required parameters in ``omnia/input/accelerator.rst``.

+----------------------+--------------------------+-----------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Name                 | Default, Accepted Values | Required? | Information                                                                                                                                                                          |
+======================+==========================+===========+======================================================================================================================================================================================+
| amd_gpu_version      | latest                   | FALSE     | Required AMD GPU driver version                                                                                                                                                      |
+----------------------+--------------------------+-----------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| amd_rocm_version     | latest                   | FALSE     | Required AMD ROCm driver version                                                                                                                                                     |
+----------------------+--------------------------+-----------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| cuda_toolkit_version | latest                   | FALSE     | Required CUDA toolkit version                                                                                                                                                        |
+----------------------+--------------------------+-----------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| cuda_toolkit_path    |                          | FALSE     | If the latest cuda toolkit is not required, provide an offline copy of   the toolkit installer in the path specified. (Take an RPM copy of the toolkit   from developer.nvidia.com/) |
+----------------------+--------------------------+-----------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| cuda_stream          | latest-dkms              | FALSE     | A stream in CUDA is a sequence of operations that execute on the device   in the order in which they are issued by the host code.                                                    |
+----------------------+--------------------------+-----------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

.. note:: For target nodes running RedHat, ensure that redhat subscription is enabled before running ``accelerator.yml``


To install all the latest GPU drivers and toolkits, run: ::

    ansible-playbook accelerator.yml -i inventory

(where inventory consists of manager, compute and login nodes)

The following configurations take place when running ``accelerator.yml``
    i. Servers with AMD GPUs are identified and the latest GPU drivers and ROCm platforms are downloaded and installed.
    ii. Servers with NVIDIA GPUs are identified and the specified CUDA toolkit is downloaded and installed.
    iii. For the rare servers with both NVIDIA and AMD GPUs installed, all the above mentioned download-ables are installed to the server.
    iv. Servers with neither GPU are skipped.
