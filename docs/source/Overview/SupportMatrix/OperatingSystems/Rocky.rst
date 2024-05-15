Rocky Linux
=============

.. caution:: **THE ROCKY LINUX OS VERSION ON THE CLUSTER WILL BE UPGRADED TO THE LATEST 8.x VERSION AVAILABLE IRRESPECTIVE OF THE PROVISION_OS_VERSION PROVIDED IN PROVISION_CONFIG.YML.**

+------------+---------------+---------------+
| OS Version | Control Plane | Cluster Nodes |
+============+===============+===============+
| 8.6        | Yes           | No            |
+------------+---------------+---------------+
| 8.7 [1]_   | Yes           | No            |
+------------+---------------+---------------+
| 8.8        | Yes           | Yes           |
+------------+---------------+---------------+

.. [1] This version of Rocky Linux does not support vLLM installation via Omnia.

.. note::
    * Always deploy the DVD (Full) Edition of the OS on cluster  nodes.
    * AMD ROCm driver installation is not supported by Omnia on Rocky Linux cluster nodes.





