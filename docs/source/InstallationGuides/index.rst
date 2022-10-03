Quick Installation Guide
========================

Choose a compute outside your intended cluster to provision and configure it. This compute needs to be internet-capable with Github installed. If you intend to provision the cluster via Infiniband NICs, install the required drivers using:

``yum groupinstall "Infiniband Support" -y``


Once the Omnia repository has been cloned on to the compute node:

    ``git clone https://github.com/dellhpc/omnia.git``

Change directory to Omnia using:

    ``cd omnia``

Run the script ``prereqs.sh`` to verify the system is ready for Omnia deployment.

.. toctree::
    :hidden:

    RunningInit/index
    RunningControlPlane/index
    RunningOmnia/index
    ConfiguringSwitches/index
    ConfiguringStorage/index



