Quick Installation Guide
========================

Choose a server outside your intended cluster to function as your control plane.

The control plane needs to be internet-capable with Github and a full OS installed.

.. note:: Omnia can be run on control planes running RHEL and Rocky. For a complete list of versions supported, check out the `Support Matrix <../Overview/SupportMatrix/OperatingSystems/index.html>`_.

::

    dnf install git -y

.. note:: If the control plane  has an Infiniband NIC installed, run the below command:

    ``yum groupinstall "Infiniband Support" -y``


To clone the Omnia repository onto the control plane, run the following command: ::

    git clone https://github.com/dell/omnia.git

Once the cloning process is complete, switch to the Omnia directory using the following command: ::

    cd omnia
    sh prereq.sh

Run the script ``prereq.sh`` to verify the system is ready for Omnia deployment.

.. note:: The permissions on the Omnia directory are set to **0755** by default. Do not change these values.

.. toctree::
    RunningInit/index
    InstallingProvisionTool/index
    PostProvisionScript
    BuildingClusters/index
    addinganewnode
    reprovisioningthecluster
    ConfiguringSwitches/index
    ConfiguringStorage/index
    Benchmarks/index
    CleanUpScript




