Before you run the provision tool
---------------------------------

* (Recommended) Run ``prereq.sh`` to get the system ready to deploy Omnia.

* All target bare-metal servers (cluster nodes) should be reachable to the chosen OIM.

* The UEFI boot setting should be configured in the BIOS settings before initiating PXE boot on the nodes.

* Admin and BMC network switches should be configured before running the provision tool. For more information on configuring the switches, `click here <../AdvancedConfigurationsRHEL/ConfiguringSwitches/index.html>`_.

* Set the IP address of the OIM. The OIM NIC connected to remote servers (through the switch) should be configured with two IPs (BMC IP and admin IP) in a shared LOM or hybrid set up. In the case dedicated network topology, a single IP (admin IP) is required.

.. figure:: ../../../images/ControlPlaneNic.png

            *OIM NIC IP configuration in a LOM setup*

.. figure:: ../../../images/ControlPlane_DedicatedNIC.png

            *OIM NIC IP configuration in a dedicated setup*


* Set the hostname of the OIM in the ``hostname``. ``domain name`` format.

    .. include:: ../../../Appendices/hostnamereqs.rst

    For example, ``controlplane.omnia.test`` is acceptable. ::

        hostnamectl set-hostname controlplane.omnia.test

.. note:: The domain name specified for the OIM should be the same as the one specified under ``domain_name`` in ``input/provision_config.yml``.

* To provision the bare metal servers, download one of the following ISOs to the OIM:

    * `RHEL 8.x <https://www.redhat.com/en/enterprise-linux-8>`_
    * `Rocky Linux 8.x <https://rockylinux.org/>`_

.. note:: Ensure the ISO provided has downloaded seamlessly (No corruption). Verify the SHA checksum/ download size of the ISO file before provisioning to avoid future failures.

Note the compatibility between cluster OS and OIM OS below:

        +---------------------+--------------------+------------------+
        |                     |                    |                  |
        | OIM OS              | Cluster  Node OS   | Compatibility    |
        +=====================+====================+==================+
        |                     |                    |                  |
        | RHEL [1]_           | RHEL               | Yes              |
        +---------------------+--------------------+------------------+
        |                     |                    |                  |
        | Rocky               | Rocky              | Yes              |
        +---------------------+--------------------+------------------+

.. [1] Ensure that OIMs running RHEL have an active subscription or are configured to access local repositories. The following repositories should be enabled on the OIM: **AppStream**, **BaseOS**.

* Ensure that all connection names under the network manager match their corresponding device names.
    To verify network connection names: ::

            nmcli connection

    To verify the device name: ::

             ip link show

In the event of a mismatch, edit the file ``/etc/sysconfig/network-scripts/ifcfg-<nic name>`` using the vi editor for RHEL/Rocky Linux clusters.

* When discovering nodes via a mapping file, all target nodes should be set up in PXE mode before running the playbook.

.. note::

    * After configuration and installation of the cluster, changing the OIM is not supported. If you need to change the OIM, you must redeploy the entire cluster.

    * For servers with an existing OS being discovered via BMC, ensure that the first PXE device on target nodes should be the designated active NIC for PXE booting.








