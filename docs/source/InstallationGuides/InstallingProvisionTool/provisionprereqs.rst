Before You Run The Provision Tool
---------------------------------

* (Recommended) Run ``prereq.sh`` to get the system ready to deploy Omnia. Alternatively, ensure that `Ansible 2.12.9 <https://docs.ansible.com/ansible/latest/reference_appendices/release_and_maintenance.html>`_ and `Python 3.8 <https://www.python.org/downloads/release/python-380/>`_ are installed on the system. SELinux should also be disabled.
* To provision the bare metal servers, download one of the following ISOs for deployment:

    1. `Rocky 8 <https://rockylinux.org/>`_

    2. `RHEL 8.x <https://www.redhat.com/en/enterprise-linux-8>`_

* To dictate IP address/MAC mapping, a host mapping file can be provided. Use the `pxe_mapping_file.csv <../../Samplefiles.html>`_ to create your own mapping file.

* Ensure that all connection names under the network manager match their corresponding device names. ::

    nmcli connection

In the event of a mismatch, edit the file  ``/etc/sysconfig/network-scripts/ifcfg-<nic name>`` using vi editor.

* When discovering nodes via SNMP or a mapping file, all target nodes should be set up in PXE mode before running the playbook.

* If RHEL is in use on the control plane, enable RedHat subscription. Not only does Omnia not enable RedHat subscription on the control plane, package installation may fail if RedHat subscription is disabled.

* Users should also ensure that all repos are available on the RHEL control plane.

* Ensure that the ``pxe_nic`` and ``public_nic`` are in the firewalld zone: public.

* All shared LOM IPs assigned should follow the convention: xx.yy.zz.1 (ie the last octet of a shared LOM IP should be 1. Eg: If the ``pxe_subnet`` provided is 172.17.0.0, the shared LOM IP assigned should be 172.17.0.1)

 .. Note::

    * After configuration and installation of the cluster, changing the control plane is not supported. If you need to change the control plane, you must redeploy the entire cluster.

    * If there are errors while executing any of the Ansible playbook commands, then re-run the playbook.

    * For servers with an existing OS being discovered via BMC, ensure that the first PXE device on target nodes should be the designated active NIC for PXE booting.








