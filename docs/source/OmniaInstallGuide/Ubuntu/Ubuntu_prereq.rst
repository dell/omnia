Prerequisites
=================

1. Choose a server outside of your intended cluster with the mentioned `storage requirements <UbuntuSpace.html>`_ to function as your Omnia control plane.

2. Ensure that the control plane has the "server install image" of the Ubuntu operating system (OS) installed. For a complete list of supported OS versions, check out the `Support Matrix <../../Overview/SupportMatrix/OperatingSystems/index.html>`_.

3. Ensure that the control plane needs is internet-capable with Git installed. If Git is not installed, use the below command to install it. ::

    dnf install git -y

4. Clone the Omnia repository from GitHub on to the control plane server using the following command: ::

    git clone https://github.com/dell/omnia.git

5. [Optional] `Set up a proxy server for the CP <Setup_CP_proxy.html>`_.
