Configuring additional NICs on the nodes
-------------------------------------------
After running ``provision.yml`` or ``discovery_provision.yml`` and the nodes boot up, additional NICs can be configured on target nodes using the ``nic_update.yml`` playbook.

**Prerequisites**

* All target nodes are provisioned and booted. `Click here to verify the status of all nodes. <ViewingDB.html>`_

* The ``input/network_spec.yml`` file has been updated with all network information in addition to admin network and bmc network information. Below are all applicable properties of an additional network:

    * ``nic_name``: The name of the NIC on which the administrative network is accessible to the control plane.
    * ``netmask_bits``: The 32-bit "mask" used to divide an IP address into subnets and specify the network's available hosts.
    * ``static_range``: The static range of IPs to be provisioned on target nodes.
    * ``dynamic_range``: The dynamic range of IPs to be provisioned on target nodes.
    * ``correlation_to_admin``: Boolean value used to indicate whether all other networks specified in the file (eg: ``bmc_network``) should be correlated to the admin network. For eg: if a target node is assigned the IP xx.yy.0.5 on the admin network, it will be assigned the IP aa.bb.0.5 on the BMC network. This value is irrelevant when discovering nodes using a mapping file.
    * ``admin_uncorrelated_node_start_ip``: If ``correlation_to_admin`` is set to true but correlated IPs are not available on non-admin networks, provide an IP within the ``static_range`` of the admin network that can be used to assign admin static IPs to uncorrelated nodes. If this is empty, then the first IP in the ``static_range`` of the admin network is taken by default. This value is irrelevant when discovering nodes using a mapping file.
    * ``CIDR``: Classless or Classless Inter-Domain Routing (CIDR) addresses use variable length subnet masking (VLSM) to alter the ratio between the network and host address bits in an IP address.
    * ``MTU``: Maximum transmission unit (MTU) is a measurement in bytes of the largest data packets that an Internet-connected device can accept.
    * ``DNS``: A DNS server is a computer equipped with a database that stores the public IP addresses linked to the domain names of websites, enabling users to reach websites using their IP addresses.
    * ``VLAN``: A 12-bit field that identifies a virtual LAN (VLAN) and specifies the VLAN that an Ethernet frame belongs to.

.. note::

    * If a ``CIDR`` value is provided, the complete subnet is used for Omnia to assign IPs and where possible, the IPs will be correlated with the assignment on the admin network.
    * If a VLAN is required, ensure that a VLAN ID is provided in the field ``vlan``. This field is not supported on admin or bmc networks.


Below is a sample of additional NIC information in a ``input/network_spec.yml`` file: ::

           - thor_network1:
              netmask_bits: "20"
              CIDR: "10.10.16.0"
              network_gateway: ""
              MTU: "1500"
              VLAN: ""

           - thor_network2:
              netmask_bits: "20"
              static_range: "10.10.1.1-10.10.15.254"
              network_gateway: ""
              MTU: "1500"
              VLAN: "1"


* The ``input/server_spec.yml`` file has been updated with all NIC information of the target nodes.

    * All NICs listed in the ``server_spec.yml`` file are grouped into categories (groups for servers). The string "Categories:" should not be edited out of the ``input/server_spec.yml`` file.
    * The name of the NIC specified in the file (in this sample, ``ensp0``, ``ensp0.5``, and ``eno1``) is the unique identifier of NICs in the file.
    * The property ``nictype`` indicates what kind of NIC is in use (ethernet, infiniband, or vlan). If the ``nictype`` is set to ``vlan``, ensure to specify a primary NIC for the VLAN using the property ``nicdevices``.
    * While new groups can be added to the ``server_spec.yml`` file on subsequent runs of the playbook, existing groups cannot be edited or deleted.

   .. note:: The ``nicnetwork`` property should match any of the networks specified in ``input/network_spec.yml``.

Below is a sample ``input/server_spec.yml`` file: ::

        ---
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

          - group-2:
            - network:
              - eno1:
                  nicnetwork: "thor_network1"
                  nictypes: "ethernet"


Use the below commands to assign IPs to the NICs: ::

    cd nic_update
    ansible-playbook nic_update -i inventory

Where the inventory file passed includes user-defined groups,servers associated with them, and a mapping from the groups specified and the categories in ``input/server_spec.yml``. Below is a sample: ::

    [waco1]
    10.5.0.3

    [waco1:vars]
    Categories=group-1

    [waco2]
    10.5.0.4
    10.5.0.5

    [waco2:vars]
    Categories=group-2

Based on the provided sample files, server 10.5.0.3 has been mapped to waco1 which corresponds to group-1. Therefore, the NICs ensp0 and ensp0.5 will be configured in an ethernet VLAN group with ens0 as the primary device.




