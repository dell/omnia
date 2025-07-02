Step 6: Execute the ``prepare_oim.yml`` playbook
==================================================

The ``prepare_oim.yml`` playbook accomplishes the following tasks:

* Sets up the PCS container: ``omnia_pcs``
* Sets up the Kubespray container (if ``k8s`` entry is present in ``/opt/omnia/input/project_default/software_config.json``): ``omnia_kubespray_<version>``
* Sets up the Provision container: ``omnia_provision``
* Sets up the Pulp container: ``pulp``
* Sets up the Squid container (if ``enable_routed_internet`` is ``true`` in ``/opt/omnia/input/project_default/local_repo_config.yml``): ``squid``
* Sets up the containers required for iDRAC telemetry service (if ``idrac_telemetry_support`` is ``true`` in ``opt/omnia/input/project/defaut/telemetry_config.yml``): ``idrac_telemetry_receiver``, ``mysqldb``, and ``activemq``
* Sets up the containers required for collecting iDRAC telemetry metrics using the Prometheus toolkit (If ``idrac_telemetry_service`` is set to ``true`` and ``idrac_telemetry_collection_type`` is ``prometheus``): ``prometheus`` and ``prometheus_pump`` 

Prerequisites
----------------

* Ensure that the system time is synchronized across all compute nodes and the OIM. Time mismatch can lead to certificate-related issues during or after the ``prepare_oim.yml`` playbook execution.
* If you intend to set up a `hierarchical cluster <xcat_hierarchical.html>`_, ensure that the ``service_node`` role has been defined in the ``/opt/omnia/input/project_default/roles_config.yml`` input file before executing ``prepare_oim.yml`` playbook.

Input files for the playbook
------------------------------

The ``prepare_oim.yml`` playbook is dependent on the inputs provided to the following input files:

* ``network_spec.yml``: This input file is located in the ``/opt/omnia/input/project_default`` folder and contains the necessary configurations for the cluster network.
* ``software_config.json``: This input file is located in the ``/opt/omnia/input/project_default`` folder and contains the details about the software packages which are to be installed on the cluster.
* ``local_repo_config.yml``: This input file is located in the ``/opt/omnia/input/project_default`` folder and contains the details about the local repositories which are to be created on the Pulp container present on the OIM.
* ``telemetry_config.yml``: This input file is located in the ``/opt/omnia/input/project_default`` folder and contains the details about running the iDRAC telemetry service on the cluster.

1. ``network_spec.yml``
------------------------

Add necessary inputs to the ``network_spec.yml`` file to configure the network on which the cluster will operate. Use the below table as reference while doing so:

.. csv-table:: network_spec.yml
   :file: ../../Tables/network_spec.csv
   :header-rows: 1
   :keepspace:

.. note::

    * If the ``nic_name`` is identical on both the ``admin_network`` and the ``bmc_network``, it indicates a LOM setup. Otherwise, it's a dedicated setup.
    * BMC network details are not required when target nodes are discovered using a mapping file.
    * If ``bmc_network`` properties are provided, target nodes will be discovered using the BMC method in addition to the methods whose details are explicitly provided in ``provision_config.yml``.
    * The strings ``admin_network`` and ``bmc_network`` should not be edited. Also, the properties ``nic_name``, ``static_range``, and ``dynamic_range`` cannot be edited on subsequent runs of the provision tool.
    * ``netmask_bits`` are mandatory and should be same for both ``admin_network`` and ``bmc_network`` (that is, between 1 and 32; 1 and 32 are also acceptable values).

.. caution::
    * Do not assign the subnet 10.4.0.0/24 to any interfaces in the network as nerdctl uses it by default.
    * All provided network ranges and NIC IP addresses should be distinct with no overlap.
    * All iDRACs must be reachable from the OIM.

A sample of the ``network_spec.yml`` where nodes are discovered using a **mapping file** is provided below: ::

    ---
         Networks:
         - admin_network:
             nic_name: "eno1"
             netmask_bits: "16"
             primary_oim_admin_ip: "10.5.255.254"
             static_range: "10.5.0.1-10.5.0.200"
             dynamic_range: "10.5.1.1-10.5.1.200"
             correlation_to_admin: true
             admin_uncorrelated_node_start_ip: "10.5.0.50"
             network_gateway: ""
             DNS: ""
             MTU: "1500"

         - bmc_network:
             nic_name: ""
             netmask_bits: ""
             static_range: ""
             dynamic_range: ""
             reassignment_to_static: true
             discover_ranges: ""
             network_gateway: ""
             MTU: "1500"

A sample of the ``network_spec.yml`` where nodes are discovered using **BMC discovery mechanism** is provided below: ::

    ---
        Networks:
        - admin_network:
            nic_name: ""
            netmask_bits: ""
            primary_oim_admin_ip: ""
            static_range: ""
            dynamic_range: ""
            correlation_to_admin: true
            admin_uncorrelated_node_start_ip: ""
            network_gateway: ""
            DNS: ""
            MTU: ""

        - bmc_network:
            nic_name: "eno1"
            netmask_bits: "16"
            static_range: "10.3.0.1-10.3.0.200"
            dynamic_range: "10.3.1.1-10.3.1.200"
            reassignment_to_static: true
            discover_ranges: ""
            network_gateway: ""
            MTU: "1500"


2. ``software_config.json``
-------------------------------

The ``/opt/omnia/input/project_default/software_config.json`` file lists all the software packages to be installed on the OIM. Edit the ``software_config.json`` file based on the software stack you want on the OIM. Use the below table as reference while doing so:

.. csv-table:: software_config.json
   :file: ../../Tables/software_config_rhel.csv
   :header-rows: 1
   :keepspace:

A sample of the ``software_config.json`` file for RHEL clusters is attached below: ::

    {
        "cluster_os_type": "rhel",
        "cluster_os_version": "9.6",
        "iso_file_path": "",
        "repo_config": "always",
        "softwares": [
            {"name": "amdgpu", "version": "6.3.1"},
            {"name": "cuda", "version": "12.8.0"},
            {"name": "ofed", "version": "24.10-1.1.4.0"},
            {"name": "service_node" },
            {"name": "openldap"},
            {"name": "nfs"},
            {"name": "k8s", "version":"1.31.4"},
            {"name": "slurm"}
        ],
        "amdgpu": [
            {"name": "rocm", "version": "6.3.1" }
        ],
        "slurm": [
            {"name": "slurm_control_node"},
            {"name": "slurm_node"},
            {"name": "login"}
        ]
    }

3. ``local_repo_config.yml``
-------------------------------

Add necessary inputs to the ``local_repo_config.yml`` file for the local repositories to be created on the Pulp container present on the OIM. Use the below table as reference while doing so:

.. csv-table:: local_repo_config.yml
   :file: ../../Tables/local_repo_config_rhel.csv
   :header-rows: 1
   :keepspace:

4. ``telemetry_config.yml``
-----------------------------

Add necessary inputs to the ``telemetry_config.yml`` file for the telemetry service. Use the below table as reference while doing so:

.. csv-table:: telemetry_config.yml
   :file: ../../Tables/telemetry_config.csv
   :header-rows: 1
   :keepspace:

Playbook execution
-------------------

After you have filled in the input files as mentioned above, execute the following commands to trigger the playbook: ::

    ssh omnia_core
    cd /omnia/prepare_oim
    ansible-playbook prepare_oim.yml

.. note:: After ``prepare_oim.yml`` execution, ``ssh omnia_core`` may fail if you switch from a non-root to root user using ``sudo`` command. To avoid this, log in directly as a ``root`` user before executing the playbook or follow the steps mentioned `here <../../Troubleshooting/KnownIssues/Common/Login.html>`_.
