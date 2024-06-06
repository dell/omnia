Ubuntu
======

========== ============= =============
OS Version Control Plane Cluster Nodes
========== ============= =============
20.04 [1]_   Yes            Yes
22.04        Yes            Yes
========== ============= =============

.. [1] This version of Ubuntu does not support vLLM and racadm installation via Omnia.

.. note::
    * Omnia uses only the "server install image" version of Ubuntu for provisioning the clusters.
    * Ubuntu does not support the use of Slurm as a clustering software. As a result, FreeIPA is not supported on Ubuntu.
    * PowerVault storage devices are not compatible with the Ubuntu operating system. As a result, Omnia running on Ubuntu clusters does not support the configuration of PowerVault storage devices.