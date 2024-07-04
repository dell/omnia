Install Omnia on Ubuntu clusters
===================================

* Step 1: `Run the prereq.sh script. <../InstallationGuides/RunningInit/index.html>`_
* Step 2: `Create offline repositories on the control plane, which will be accessed by all the cluster nodes. <../InstallationGuides/LocalRepo/index.html>`_
* Step 3: `Install, configure, and execute the cluster provision tool. This tool discovers potential cluster nodes and installs OS on them. <../InstallationGuides/InstallingProvisionTool/index.html>`_
* Step 4: `Create cluster inventory files out of all the cluster nodes. <../InstallationGuides/PostProvisionScript.html>`_
* Step 5: `Configure and build the cluster <../InstallationGuides/BuildingClusters/index.html>`_
    - `Build your cluster <../InstallationGuides/BuildingClusters/installscheduler.html>`_
    - `Install Kubernetes on the cluster <../InstallationGuides/BuildingClusters/install_kubernetes.html>`_
    - `Set up centralized authentication on the cluster <../InstallationGuides/BuildingClusters/Authentication.html>`_
* Step 6: `Install AI tools on the cluster <../InstallationGuides/Platform/index.html>`_

.. note::
    - Slurm installation is not supported on Ubuntu.
    - FreeIPA configuration is not supported on Ubuntu.