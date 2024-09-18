Configuring additional NICs and Kernel Parameters on the nodes
----------------------------------------------------------------
After the ``discovery_provision.yml`` playbook has been executed and the nodes have booted up, additional NICs or OS Kernel command-line parameters can be configured on the cluster nodes using the ``server_spec_update.yml`` playbook. For more information about the supported kernel command-line parameters, `click here <https://docs.kernel.org/admin-guide/kernel-parameters.html>`_.
The ``server_spec_update.yml`` playbook can be used to do the following tasks:

    * Configure additional NICs on the nodes.
    * Configure OS Kernel command-line parameters on the nodes.
    * Configure both additional NICs and OS Kernel command-line parameters on the nodes.

**Prerequisites**

* All target nodes are provisioned and booted. `Click here <../OmniaInstallGuide/Ubuntu/Provision/ViewingDB.html>`_ to know how to verify the status of the nodes.

* Ensure that ``input/network_spec.yml`` file has been updated with all network information in addition to ``admin_network`` and ``bmc_network`` information. Below are all applicable properties of an additional network:

    * ``nic_name``: The name of the NIC on which the administrative network is accessible to the control plane.
    * ``netmask_bits``: The 32-bit "mask" used to divide an IP address into subnets and specify the network's available hosts.
    * ``static_range``: The static range of IPs to be provisioned on target nodes. This indicates that only a certain static range is available to Omnia.

* In addition to the above mentioned properties, the following properties are also applicable and can be added in ``input/network_spec.yml`` for additional NICs:

    * ``CIDR``: Classless or Classless Inter-Domain Routing (CIDR) addresses use variable length subnet masking (VLSM) to alter the ratio between the network and host address bits in an IP address.

      .. note:: You can either use ``CIDR`` or ``static_range``. Simultaneous use of both parameters will result in an error message being displayed.

    * ``MTU``: Maximum transmission unit (MTU) is a measurement in bytes of the largest data packets that an Internet-connected device can accept. Default value of ``MTU`` is 1500. You can enter your desired value.
    * ``VLAN``: A 12-bit field that identifies a virtual LAN (VLAN) and specifies the VLAN that an ethernet frame belongs to. This property is not supported on clusters running Ubuntu.

* Modify the ``input/server_spec.yml`` file with the additional NIC information and/or OS command-line kernel parameters that you want to add or alter for the target nodes. Ensure the following:

    * All NICs listed in the ``server_spec.yml`` file are grouped into categories (groups for servers). The field ``Categories:`` should not be edited out of the ``input/server_spec.yml`` file.
    * The name of the NIC specified in the file (in this sample, ``ensp0``, ``ensp0.5``, and ``eno1``) is the unique identifier of NICs in the file.
    * The property ``nictype`` indicates what kind of NIC is in use (ethernet, infiniband, or vlan). If the ``nictype`` is set to ``vlan``, ensure to specify a primary NIC for the VLAN using the property ``nicdevices``.
    * The OS Kernel command-line parameters should be provided under ``cmdline`` field. If you want to provide multiple kernel parameters, ensure that they are separated by a "space".

.. note::

    * If a ``static_range`` value is provided in ``input/network_spec.yml``, additional networks are not correlated.
    * If a ``CIDR`` value is provided in ``input/network_spec.yml``, the complete subnet is used for Omnia to assign IPs and where possible, the IPs will be correlated with the assignment on the admin network. Omnia performs correlation for additional networks if the subnet prefix for the admin network is a superset, and the additional network is a subset. For example, if the subnet prefix for the admin network is */16* and for the additional network it's */24*, Omnia attempts to correlate the IPs if the value for the ``correlate_to_admin`` field is set to true in ``input/network_spec.yml``.
    * If a VLAN is required, ensure that a VLAN ID is provided in the ``vlan`` field in ``input/server_spec.yml`` and ensure that it's provided in the ``NIC.vlan_id`` format. For example, consider "eth1.101" where ``eth1`` is the NIC name configured with a VLAN is and ``101`` is the ``vlan_id``. This field is not supported on admin or bmc networks.
    * While new networks can be added to the ``network_spec.yml`` file on subsequent runs of the ``server_spec_update.yml`` playbook, existing networks cannot be edited or deleted. If the user modifies or removes existing networks from ``input/network_spec.yml``, the playbook execution might fail. In that case, the user needs to `reprovision the node <../OmniaInstallGuide/Maintenance/reprovision.html>`_.

**Usage Instructions**

* *Configure additional NICs on the nodes.*

    * Fill up all the necessary details for the additional NICs in the ``input/network_spec.yml`` file. You can refer the following sample: ::

        - thor_network1:
           netmask_bits: "24"
           CIDR: "10.23.1.0"
           network_gateway: ""
           MTU: "1500"
           VLAN: ""
        - thor_network2:
           netmask_bits: "24"
           static_range: "10.23.2.1-10.23.2.254"
           network_gateway: ""
           MTU: "1500"
           VLAN: "1"

    * Add the additional NIC information to the ``input/server_spec.yml`` file. You can refer the following sample: ::

        Categories:
          - group-1:
              - network:
                  - ensp0:
                      nicnetwork: "thor_network1"
                      nictypes: "ethernet"
                  - ensp0.5:
                      nicnetwork: "thor_network2"
                      nictypes: "vlan"
                      nicdevices: "ensp0"



* *Configure OS Kernel command-line parameters on the nodes.*

    * Do not change anything in the ``input/network_spec.yml`` file.

    * Add the OS Kernel command-line parameters to the ``cmdline`` field in the ``input/server_spec.yml`` file. You can refer the following sample: ::

        Categories:
           - group-1:
               - os:
                   - kernel:
                       - cmdline: "iommu=pt intel_iommu=off pci=realloc=off processor.max_cstate=0 intel_idle.max_cstate=0 intel_pstate=disable"



* *Configure both additional NICs and OS Kernel command-line parameters on the nodes.*

    * Fill up all the necessary details for the additional NICs in the ``input/network_spec.yml`` file. You can refer the following sample: ::

        - thor_network1:
           netmask_bits: "24"
           CIDR: "10.23.1.0"
           network_gateway: ""
           MTU: "1500"
           VLAN: ""
        - thor_network2:
           netmask_bits: "24"
           static_range: "10.23.2.1-10.23.2.254"
           network_gateway: ""
           MTU: "1500"
           VLAN: "1"

    * Add the OS Kernel command-line parameters to the ``cmdline`` field in the ``input/server_spec.yml`` file. You can refer the following sample: ::

        Categories:
          - group-1:
              - network:
                  - ensp0:
                      nicnetwork: "thor_network1"
                      nictypes: "ethernet"
                  - ensp0.5:
                      nicnetwork: "thor_network2"
                      nictypes: "vlan"
                      nicdevices: "ensp0"
              - os:
                  - kernel:
                      - cmdline: "iommu=pt intel_iommu=off pci=realloc=off processor.max_cstate=0 intel_idle.max_cstate=0 intel_pstate=disable"

.. note::

    * If OS Kernel command-line parameter configuration is not required on the nodes, the user can leave the ``cmdine`` entry empty in ``input/server_spec.yml`` or remove the ``os`` section.
    * The ``nicnetwork`` details must be consistent with the network names specified in the ``input/network_spec.yml`` file.
    * While new groups can be added to the ``input/server_spec.yml`` file on subsequent runs of the ``server_spec_update.yml`` playbook, existing groups cannot be edited or deleted. If the user modifies or removes existing groups from ``input/server_spec.yml``, the playbook execution might fail. In that case, the user needs to `reprovision the node <../../Maintenance/reprovision.html>`_.
    * This playbook has been validated with the following Kernel parameters:

            * iommu=pt
            * intel_iommu=off
            * pci=realloc=off
            * processor.max_cstate=0
            * intel_idle.max_cstate=0
            * intel_pstate=disable

.. caution:: When running the playbook for multiple times, it’s the user's responsibility to ensure that they only provide new or updated values for the command-line parameters. The same parameters with their original values should not be re-provided to avoid configuration conflicts.

**Executing the playbook**

After you have filled up the ``input/network_spec.yml`` and ``input/server_spec.yml`` with all the necessary details based on the configuration(s) required, do the following to execute the playbook:

* First, create an inventory while referencing the sample inventory format is present in ``examples/server_spec_inv`` and also attached below: ::

    [node-group1]
    10.5.0.3

    [node-group1:vars]
    Categories=group-1

    [node-group2]
    10.5.0.4
    10.5.0.5

    [node-group2:vars]
    Categories=group-2

In the above sample inventory file, ``[node-group1]`` and ``[node-group2]`` are user-defined groups with servers associated to them. The groups are mapped and categorised in ``input/server_spec.yml`` under ``[<group name>:vars]``.

.. note:: While creating the inventory file, ensure that each group has unique nodes. One node should not be part of two groups.

* Finally, use the below command to execute the playbook: ::

    cd utils/server_spec_update
    ansible-playbook server_spec_update.yml -i <inventory_file_path>

.. note:: In Omnia v1.6, while executing ``server_spec_update.yml``, the user needs to ensure that only admin IP addresses are used in the inventory file, not service tags or node names.

Based on the provided sample files, server 10.5.0.3 has been mapped to node-group1 which corresponds to group-1. Therefore, the NICs ensp0 and ensp0.5 will be configured in an ethernet VLAN group with ensp0 as the primary device.




