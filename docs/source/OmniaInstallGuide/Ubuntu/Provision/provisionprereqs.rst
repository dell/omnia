Before you run the provision tool
---------------------------------

* (Recommended) Run ``prereq.sh`` to get the system ready to deploy Omnia. Alternatively, ensure that `Ansible 2.14 <https://docs.ansible.com/ansible/latest/reference_appendices/release_and_maintenance.html>`_ and `Python 3.9 <https://www.python.org/downloads/>`_ are installed on the system.

* All target bare-metal servers (cluster nodes) should be reachable from the chosen control plane.

* The UEFI boot setting should be configured in the BIOS settings before initiating PXE boot on the nodes.

* Set the IP address of the control plane. The control plane NIC connected to remote servers (through the switch) should be configured with two IPs (BMC IP and admin IP) in a `shared LOM <../../../Overview/NetworkTopologies/lom.html>`_ or `hybrid <../../../Overview/NetworkTopologies/Hybrid.html>`_ setup. In the case of a `dedicated <../../../Overview/NetworkTopologies/dedicated.html>`_ setup, a single IP (admin IP) is required. For more information on configuring the switches, `click here <../AdvancedConfigurationsUbuntu/ConfiguringSwitches/index.html>`_.

.. figure:: ../../../images/ControlPlaneNic.png

            *Control plane NIC IP configuration in a LOM or Hybrid setup*

.. figure:: ../../../images/ControlPlane_DedicatedNIC.png

            *Control plane NIC IP configuration in a dedicated setup*


* Set the hostname of the control plane in the ``<hostname>.<domain_name>`` format.

    .. include:: ../../../Appendices/hostnamereqs.rst

    For example, ``controlplane.omnia.test`` is acceptable. ::

        hostnamectl set-hostname controlplane.omnia.test

.. note:: The domain name specified for the control plane should be the same as the one specified under ``domain_name`` in ``input/provision_config.yml``.

* To provision the bare metal servers, download the following ISO to the control plane:

    `Ubuntu <https://ubuntu.com/download/server>`_

.. note:: Ensure the ISO provided has downloaded seamlessly (not corrupted). Verify the SHA checksum/ download size of the ISO file before provisioning to avoid future failures.

Note the compatibility between cluster OS and control plane OS below:

        +---------------------+--------------------+------------------+
        |                     |                    |                  |
        | Control Plane OS    | Cluster  Node OS   | Compatibility    |
        +=====================+====================+==================+
        |                     |                    |                  |
        | Ubuntu              | Ubuntu             | Yes              |
        +---------------------+--------------------+------------------+
        |                     |                    |                  |
        | Rocky               | Ubuntu             | No               |
        +---------------------+--------------------+------------------+
        |                     |                    |                  |
        | RHEL                | Ubuntu             | No               |
        +---------------------+--------------------+------------------+
        |                     |                    |                  |
        | Ubuntu              | RHEL               | No               |
        +---------------------+--------------------+------------------+
        |                     |                    |                  |
        | Ubuntu              | Rocky              | No               |
        +---------------------+--------------------+------------------+

* Ensure that all connection names under the network manager match their corresponding device names.

    To verify network connection names: ::

            nmcli connection

    To verify the device name: ::

             ip link show

In the event of a mismatch, edit the file ``/etc/sysconfig/network-scripts/ifcfg-<nic name>`` using "vi editor".

* When discovering nodes via a mapping file, all target nodes should be set up in PXE mode before running the playbook.

.. note::

    * After configuration and provisioning of the cluster, changing the control plane server is not supported. If you need to change the control plane, you must redeploy the entire cluster.

    * For servers with an existing OS being discovered via BMC, ensure that the first PXE device on target nodes should be the designated active NIC for PXE booting.








