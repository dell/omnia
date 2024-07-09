Quick Installation Guide
========================

* Choose a server outside your intended cluster to function as your control plane.

* Ensure that the control plane server meets the below mentioned space requirements:

    * For all available software packages that Omnia supports: 50GB
    * For the complete set of software images (in ``/var``): 500GB
    * For storing offline repositories (the file path should be specified in ``repo_store_path`` in ``input/local_repo_config.yml``): 50GB

* The control plane needs to be internet-capable with Git installed. Additionally, the control plane must have a full-featured operating system installed.

.. note:: Omnia can be run on control planes running RHEL, Rocky Linux, and Ubuntu. For a complete list of versions supported, check out the `Support Matrix <../Overview/SupportMatrix/OperatingSystems/index.html>`_.

To install Git on RHEL and Rocky Linux installations, use the following command: ::

    dnf install git -y

To install Git on Ubuntu installations, use the following command: ::

    apt install git -y

.. note:: Optionally, if the control plane has an Infiniband NIC installed on RHEL or Rocky Linux, run the below command:
    ::
        yum groupinstall "Infiniband Support" -y

* Clone the Omnia repository from GitHub on to the control plane, using the following command: ::

    git clone https://github.com/dell/omnia.git

* Once the cloning process is complete, change directory to Omnia and run the ``prereq.sh`` script to verify that the system is ready for Omnia deployment, using the following command: ::

    cd omnia
    ./prereq.sh

.. note:: The permissions on the Omnia directory are set to **0755** by default. Do not change these values.

.. toctree::
    RunningInit/index
    LocalRepo/index
    InstallingProvisionTool/index
    PostProvisionScript
    BuildingClusters/index
    Platform/index
    addinganewnode
    reprovisioningthecluster
    ConfiguringSwitches/index
    ConfiguringStorage/index
    Benchmarks/index
    pullimagestonodes
    deletenode
    CleanUpScript




