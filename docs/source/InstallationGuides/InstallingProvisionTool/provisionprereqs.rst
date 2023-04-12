Before you run the provision tool
---------------------------------

* (Recommended) Run ``prereq.sh`` to get the system ready to deploy Omnia. Alternatively, ensure that `Ansible 2.12.10 <https://docs.ansible.com/ansible/latest/reference_appendices/release_and_maintenance.html>`_ and `Python 3.8 <https://www.python.org/downloads/release/python-380/>`_ are installed on the system. SELinux should also be disabled.
* Set the hostname of the control plane using the ``hostname``. ``domain name`` format. Create an entry in the ``/etc/hosts`` file on the control plane.

    .. include:: ../../Appendices/hostnamereqs.rst

    For example, ``controlplane.omnia.test`` is acceptable.

.. note:: The domain name specified for the control plane should be the same as the one specified under ``domain_name`` in ``input/provision_config.yml``.

* To provision the bare metal servers, download one of the following ISOs for deployment:

    1. `Rocky 8 <https://rockylinux.org/>`_

    2. `RHEL 8.x <https://www.redhat.com/en/enterprise-linux-8>`_

Note the compatibility between cluster OS and control plane OS below:

        +---------------------+--------------------+------------------+
        |                     |                    |                  |
        | Control Plane OS    | Compute Node OS    | Compatibility    |
        +=====================+====================+==================+
        |                     |                    |                  |
        | RHEL                | RHEL               | Yes              |
        +---------------------+--------------------+------------------+
        |                     |                    |                  |
        | RHEL                | Rocky              | Yes              |
        +---------------------+--------------------+------------------+
        |                     |                    |                  |
        | Rocky               | RHEL               | No               |
        +---------------------+--------------------+------------------+
        |                     |                    |                  |
        | Rocky               | Rocky              | Yes              |
        +---------------------+--------------------+------------------+

* To set up CUDA and OFED using the provisioning tool, download the required repositories from here:

    1. `CUDA <https://developer.nvidia.com/cuda-downloads/>`_

    2. `OFED <https://network.nvidia.com/products/infiniband-drivers/linux/mlnx_ofed/>`_

* To dictate IP address/MAC mapping, a host mapping file can be provided. Use the `pxe_mapping_file.csv <../../samplefiles.html>`_ to create your own mapping file.

* Ensure that all connection names under the network manager match their corresponding device names. ::

    nmcli connection

In the event of a mismatch, edit the file  ``/etc/sysconfig/network-scripts/ifcfg-<nic name>`` using vi editor.

* When discovering nodes via snmpwalk or a mapping file, all target nodes should be set up in PXE mode before running the playbook.

* Nodes provisioned using the Omnia provision tool do not require a RedHat subscription to run ``provision.yml`` on RHEL target nodes.

* For RHEL target nodes not provisioned by Omnia, ensure that RedHat subscription is enabled on all target nodes. Every target node will require a RedHat subscription.

* Users should also ensure that all repos are available on the RHEL control plane.

* Ensure that the ``pxe_nic`` and ``public_nic`` are in the firewalld zone: public.

* The control plane NIC connected to remote servers (through the switch) should be configured with two IPs in a shared LOM set up. This NIC is configured by Omnia with the IP xx.yy.255.254, aa.bb.255.254 (where xx.yy are taken from ``bmc_nic_subnet`` and aa.bb are taken from ``admin_nic_subnet``) when ``network_interface_type`` is set to ``lom``. For other discovery mechanisms, only the admin NIC is configured with aa.bb.255.254 (Where aa.bb is taken from ``admin_nic_subnet``).

.. image:: ../../../images/ControlPlaneNic.png

 .. note::

    * After configuration and installation of the cluster, changing the control plane is not supported. If you need to change the control plane, you must redeploy the entire cluster.

    * If there are errors while executing any of the Ansible playbook commands, then re-run the playbook.

    * For servers with an existing OS being discovered via BMC, ensure that the first PXE device on target nodes should be the designated active NIC for PXE booting.








