Quick Installation Guide
========================

Choose a server outside your intended cluster to function as your control plane.

The control plane needs to be internet-capable with Github and a full OS installed.

.. note:: Omnia can be run on control planes running RHEL and Rocky. For a complete list of versions supported, check out the `Support Matrix <../Overview/SupportMatrix/OperatingSystems/index.html>`_ .

::

    dnf install git -y

If the control plane  has an Infiniband NIC installed, run the below ::

    yum groupinstall "Infiniband Support" -y

Use the image below to set up your network:

.. image:: ../images/SharedLomRoceNIC.jpg


Once the Omnia repository has been cloned on to the control plane: ::

    git clone https://github.com/dellhpc/omnia.git

Change directory to Omnia using: ::

    cd omnia
    sh prereq.sh

Run the script ``prereq.sh`` to verify the system is ready for Omnia deployment.

.. toctree::
    RunningInit/index
    InstallingProvisionTool/index
    BuildingClusters/index
    ConfiguringSwitches/index
    ConfiguringStorage/index
    addinganewnode
    reprovisioningthecluster
    CleanUpScript



