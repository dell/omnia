Red Hat Enterprise Linux
========================

========== ============= =============
OS Version Control Plane Cluster  Nodes
========== ============= =============
8.1        No            Yes
8.2        No            Yes
8.3        No            Yes
8.4        Yes           Yes
8.5        Yes           Yes
8.6        Yes           Yes
8.7        Yes           Yes
========== ============= =============

.. note::
    * Always deploy the DVD Edition of the OS on cluster  nodes to access offline repos.
    * For RHEL 8.5 and below, ensure that RHEL subscription is enabled OR sshpass is available to install or download to the control plane (from any local repository).
