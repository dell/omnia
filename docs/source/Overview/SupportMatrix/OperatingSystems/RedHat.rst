Red Hat Enterprise Linux
========================

========== ============= =============
OS Version Control Plane Compute Nodes
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
    * Always deploy the DVD Edition of the OS on compute nodes to access offline repos.
    * For RHEL 8.6 and below, ensure that RHEL subscription is enabled OR sshpass is available to install or download to the control plane (from any local repository).
    * While Omnia may work with RHEL 8.4 and above, all Omnia testing was done with RHEL 8.4 on the control plane. All minor versions of RHEL 8 are supported on the compute nodes.
