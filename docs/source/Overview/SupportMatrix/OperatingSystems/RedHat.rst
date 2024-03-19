Red Hat Enterprise Linux
========================

========== ============= =============
OS Version Control Plane Cluster  Nodes
========== ============= =============
8.6 [1]_   Yes           Yes
8.7        Yes           Yes
8.8        Yes           Yes
========== ============= =============

.. [1]:: This version of RHEL does not support vLLM installation via Omnia.

.. note::
    * Always deploy the DVD Edition of the OS on cluster  nodes to access offline repos.
    * For RHEL 8.5 and below, ensure that RHEL subscription is enabled OR sshpass is available to install or download to the control plane (from any local repository).
