Provisioning the cluster
============================

The ``discovery_provision.yml`` playbook discovers the probable bare-metal cluster nodes and provisions the minimal version of RHEL OS onto those nodes. This playbook is dependent on inputs from the following input files:

* ``input/provision_config.yml``
* ``input/provision_config_credentials.yml``
* ``input/network_spec.yml``

.. note:: The first PXE device on target nodes should be the designated active NIC for PXE booting.

    .. image:: ../../../images/BMC_PXE_Settings.png
        :width: 600px

Configurations made by the ``discovery_provision.yml`` playbook
-----------------------------------------------------------------

* Discovers all target servers.
* PostgreSQL database is set up with all relevant cluster information such as MAC IDs, hostname, admin IP, BMC IPs etc.
* Configures the OIM with NTP services for cluster  node synchronization.
* The minimal version of the RHEL operating system is provisioned on the primary disk partition on the nodes. If a BOSS Controller card is available on the target node, the operating system is provisioned on the BOSS card.

[Optional] Additional configuration handled by the provision tool
-------------------------------------------------------------------------

**Disk partitioning**

* Omnia now allows for customization of disk partitions applied to remote servers. The disk partition ``desired_capacity`` has to be provided in MB. Valid ``mount_point`` values accepted for disk partition are  ``/var``, ``/tmp``, ``/usr``, ``swap``. The default partition sizes provided for RHEL are:

  * ``/boot``: 1024MB,
  * ``/boot/efi``: 256MB
  * ``/`` partition: Remaining space.

* Values are accepted in the form of JSON list such as: ::

    disk_partition:
        - { mount_point: "/var", desired_capacity: "102400" }
        - { mount_point: "swap", desired_capacity: "10240" }

**Installation of additional software packages**

Apart from the packages listed in the ``/opt/omnia/input/project_default/software_config.json`` file, additional software can also be installed on the cluster nodes during cluster provisioning. TO do so, follow the below steps:

    1. First, fill up the ``additional_software.json`` and ``software_config.json`` input files.
    2. Then, execute the ``local_repo.yml`` playbook in order to download the required packages.
    3. Finally, execute the ``discover_and_provision.yml`` playbook in order to provision the cluster nodes along with the new additional software packages.

For more information on how to fill up the input files, `click here <../../../Utils/software_update.html>`_.

Playbook execution
----------------------

To deploy the Omnia provision tool, execute the following commands: ::

    ssh omnia_core
    cd /omnia
    ansible-playbook discovery_provision.yml

.. note::

    * If the ``input/software_config.json`` has AMD ROCm and NVIDIA CUDA drivers mentioned, the AMD and NVIDIA accelerator drivers are installed on the nodes post provisioning.

    * After executing ``discovery_provision.yml`` playbook, user can check the log file available at ``/var/log/omnia.log`` for more information.

    * Ansible playbooks by default run concurrently on 5 nodes. To change this, update the ``forks`` value in ``ansible.cfg`` present in the respective playbook directory.

    * While the ``admin_nic`` on cluster nodes is configured by Omnia to be static, the public NIC IP address should be configured by user.

    * If the target nodes were discovered using switch-based or mapping mechanisms, manually PXE boot the target servers after the ``discovery_provision.yml`` playbook is executed and the target node lists as **booted** in the `nodeinfo table <ViewingDB.html>`_.

    * All ports required for xCAT to run will be opened (For a complete list, check out the `Security Configuration Document <../../../SecurityConfigGuide/ProductSubsystemSecurity.html#firewall-settings>`_).

    * After running ``discovery_provision.yml``, the file ``input/provision_config_credentials.yml`` will be encrypted. To edit the file, use the command: ``ansible-vault edit provision_config_credentials.yml --vault-password-file .provision_credential_vault_key``

    * Post execution of ``discovery_provision.yml``, IPs/hostnames cannot be re-assigned by changing the mapping file. However, the addition of new nodes is supported as explained `here <../../Maintenance/addnode.html>`_.

.. caution::

    * To avoid breaking the password-less SSH channel on the OIM, do not run ``ssh-keygen`` commands post execution of ``discovery_provision.yml`` to create a new key.

    * Do not delete the Omnia shared path or the NFS directory.

**Next steps**:

* After successfully running ``discovery_provision.yml``, go to `Building Clusters <../OmniaCluster/index.html>`_ to setup Kubernetes, NFS, BeeGFS, and Authentication.

* To create a node inventory in ``/opt/omnia``, `click here <../ViewInventory.html>`_.
