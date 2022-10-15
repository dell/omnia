Quick Installation Guide
========================

Choose a compute outside your intended cluster to provision and configure it. This compute needs to be internet-capable with Github and a full OS (Rocky or RedHat) installed. ::

    dnf install epel-release -y (For computes running Rocky)
    dnf install git -y

If you intend to provision the cluster via Infiniband NICs, install the required drivers using: ``yum groupinstall "Infiniband Support" -y``

Use the image below to set up your network:

.. image:: ../images/SharedLomRoceNIC.png


Once the Omnia repository has been cloned on to the compute node: ::

    git clone https://github.com/dellhpc/omnia.git

Change directory to Omnia using: ::

    cd omnia
    chmod +x prereq.sh

Run the script ``prereqs.sh`` to verify the system is ready for Omnia deployment.

.. toctree::
    :hidden:

    RunningInit/index
    InstallingProvisionTool/index
    BuildingClusters/index
    ConfiguringSwitches/index
    ConfiguringStorage/index



