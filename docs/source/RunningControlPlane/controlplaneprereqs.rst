Before You Run Control Plane
============================


* To provision the bare metal servers, download one of the following ISOs for deployment:

    1. `Leap 15.3 <https://get.opensuse.org/leap/>`_

    2. `Rocky 8 <https://rockylinux.org/>`_

    3. `Red Hat 8.x <https://www.redhat.com/en/enterprise-linux-8>`_

* If devices (switches, servers and storage) are to be configured and managed by Omnia, ensure that DHCP is enabled on all target devices.

* For DHCP configuration, you can provide a host mapping file. If the mapping file is not provided and the variable is left blank, a default mapping file will be created. The provided details must be in the format: MAC address, Hostname, IP address, Component_role. For example,  ``10:11:12:13,server1,100.96.20.66,compute`` and   ``14:15:16:17,server2,100.96.22.199,manager`` are valid entries.

* Connect one of the Ethernet cards on the control plane to the HPC switch. The other Ethernet card must be connected to the internet network. Acceptable network topologies are provided in the `Supported Network Topology file. <../Overview/NetworkTopologies/index.html>`_

* Ensure that all connection names under the network manager match their corresponding device names. This can be verified using the command  ``nmcli connection``. In the event of a mismatch, edit the file  ``/etc/sysconfig/network-scripts/ifcfg-<nic name>`` using vi editor.

* If Red Hat is in use on the control plane, enable RedHat subscription. Not only does Omnia not enable RHEL subscription on the control plane, package installation may fail if RHEL subscription is disabled.

* Users should also ensure that all repos are available on the Red Hat control plane.

* On the control plane, run the following commands to install Git.::


    dnf install epel-release -y (Only if Rocky is in use on the control plane)

    dnf install git -y

 .. Note::

    * After the installation of the Omnia appliance, changing the control plane is not supported. If you need to change the control plane, you must redeploy the entire cluster.

    * If there are errors while executing any of the Ansible playbook commands, then re-run the commands.

.. include:: ../Appendices/hostnamereqs.rst


* Fill in all required parameters under  ``/control_plane/input_parameters`` and security parameters under  ``omnia_security_config.yml``/  ``security_vars.yml``.
