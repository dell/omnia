Prerequisites
=================

1. Choose a server outside of your intended cluster with the mentioned `storage requirements <UbuntuSpace.html>`_ to function as your Omnia Infrastructure Manager (OIM).

2. Ensure that the OIM has the "server install image" of the Ubuntu operating system (OS) installed. For a complete list of supported OS versions, check out the `Support Matrix <../../Overview/SupportMatrix/OperatingSystems/index.html>`_.

3. Ensure that the OIM needs is internet-capable with Git installed. If Git is not installed, use the below command to install it. ::

    apt install git -y

4. Clone the Omnia repository from GitHub on to the OIM server using the following command: ::

    git clone https://github.com/dell/omnia.git

.. note:: If you do not specify a branch while cloning the repository, the ``omnia/main`` branch is cloned by default. To clone a specific branch, add ``-b <branch name>`` at the end of the git clone command. For example:
    ::
        git clone https://github.com/dell/omnia.git -b v1.7.1

5. [Optional] `Set up a proxy server for the OIM <Setup_CP_proxy.html>`_.
