Prerequisites
=================

1. Choose a server outside your intended cluster to function as your Omnia control plane. To know more information about setting up the control plane, `click here <../setup_CP.html>`_.

2. Ensure that the control plane has the "server install image" of the Ubuntu operating system (OS) installed. For a complete list of supported OS versions, check out the `Support Matrix <../../Overview/SupportMatrix/OperatingSystems/index.html>`_.

3. Ensure that the control plane meets the `space requirements <UbuntuSpace.html>`_ indicated by Omnia.

4. Ensure that the control plane needs is internet-capable with Git installed. If Git is not installed, use the below commands to install it. ::

    dnf install git -y

5. Clone the Omnia repository from GitHub on to the control plane server using the following command: ::

    git clone https://github.com/dell/omnia.git

