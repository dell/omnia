Quick Installation Guide
========================

Choose a server outside your intended cluster to function as your control plane.

The control plane needs to be internet-capable with Github and a full OS installed.

.. note:: Omnia can be run on control planes running RHEL, Rocky Linux, and Ubuntu. For a complete list of versions supported, check out the `Support Matrix <../Overview/SupportMatrix/OperatingSystems/index.html>`_ .

For RHEL and Rocky Linux installations:

::

    dnf install git -y

For Ubuntu installations:

::

    apt install git -y


.. note:: Optionally, if the control plane  has an Infiniband NIC installed on RHEL or Rocky Linux, run the below command:

    ``yum groupinstall "Infiniband Support" -y``


Once the Omnia repository has been cloned on to the control plane: ::

    git clone https://github.com/dell/omnia.git

Change directory to Omnia using: ::

    cd omnia
    ./prereq.sh

Run the script ``prereq.sh`` to verify the system is ready for Omnia deployment.

.. note:: The permisssions on the Omnia directory are set to **0755** by default. Do not change these values.

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




