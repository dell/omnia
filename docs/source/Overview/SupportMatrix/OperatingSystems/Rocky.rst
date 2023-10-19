Rocky
=====

.. caution:: **THE ROCKY LINUX OS VERSION ON THE CLUSTER WILL BE UPGRADED TO THE LATEST 8.x VERSION AVAILABLE IRRESPECTIVE OF THE PROVISION_OS_VERSION PROVIDED IN PROVISION_CONFIG.YML.**

+------------+---------------+---------------+
| OS Version | Control Plane | Compute Nodes |
+============+===============+===============+
| 8.4        | Yes           | No            |
+------------+---------------+---------------+
| 8.5        | Yes           | No            |
+------------+---------------+---------------+
| 8.6        | Yes           | No            |
+------------+---------------+---------------+
| 8.7        | Yes           | No            |
+------------+---------------+---------------+
| 8.8        | Yes           | Yes           |
+------------+---------------+---------------+

.. note::
    * Always deploy the DVD (Full) Edition of the OS on Compute Nodes.
    * AMD ROCm driver installation is not supported by Omnia on Rocky compute nodes.
    * If the control plane is running on the minimal edition of the OS, ensure that ``chrony`` and ``podman`` are installed before running ``provision.yml``.




