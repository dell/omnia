Omnia Installation Guide
=========================

Prerequisites
--------------

1. Choose a server outside your intended cluster to function as your control plane.

2. Ensure that the control plane has a full-featured operating system (OS) installed. Currently Omnia supports RHEL, RockyLinux, and Ubuntu OS on the control plane. For a complete list of supported OS versions, check out the `Support Matrix <../Overview/SupportMatrix/OperatingSystems/index.html>`_.

3. Ensure that the control plane server meets the space requirements, based on the OS:

    - `RHEL/RockyLinux <SpaceRequirements/RHELSpace.html>`_
    - `Ubuntu <SpaceRequirements/UbuntuSpace.html>`_

4. The control plane needs to be internet-capable with Git installed. If Git is not installed, use the below commands to install it.

    - To install Git on RHEL and Rocky Linux installations, use the following command: ::

          dnf install git -y

    - To install Git on Ubuntu installations, use the following command: ::

          apt install git -y

.. note:: If the control plane server (running on RHEL or Rocky Linux OS) has an Infiniband NIC installed, run the below command to install the hardware drivers and Infiniband-related packages:
    ::
        yum groupinstall "Infiniband Support" -y


Cloning the Omnia repository from Github
-----------------------------------------

Clone the Omnia repository from GitHub on to the control plane server using the following command: ::

    git clone https://github.com/dell/omnia.git


Change directory to Omnia
--------------------------

Once the cloning process is complete, change directory to Omnia using the following command: ::

    cd omnia


Install Omnia
--------------

Based on your OS type on the control plane, follow the flow mentioned in the below options:

* `Install Omnia on Red Hat Enterprise Linux (RHEL) clusters <RHEL/index.html>`_


.. toctree::
    RHEL/index
    RockyLinux
    Ubuntu