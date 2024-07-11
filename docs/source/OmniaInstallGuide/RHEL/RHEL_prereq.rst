Prerequisites
--------------

1. Choose a server outside your intended cluster to function as your control plane.

2. Ensure that the control plane has a full-featured RHEL operating system (OS) installed. For a complete list of supported OS versions, check out the `Support Matrix <../Overview/SupportMatrix/OperatingSystems/index.html>`_.

3. Ensure that the control plane meets the `space requirements <RHELSpace.html>`_ indicated by Omnia.

4. Ensure that the control plane needs is internet-capable with Git installed. If Git is not installed, use the below commands to install it. ::

    dnf install git -y

.. note:: If the control plane server has an Infiniband NIC installed, run the below command to install the hardware drivers and Infiniband-related packages:
    ::
        yum groupinstall "Infiniband Support" -y

5. Clone the Omnia repository from GitHub on to the control plane server using the following command: ::

    git clone https://github.com/dell/omnia.git

6. Once the cloning process is complete, change directory to Omnia using the following command: ::

    cd omnia