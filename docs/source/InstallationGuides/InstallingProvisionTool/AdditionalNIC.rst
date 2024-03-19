Configuring additional NICs on the nodes
-------------------------------------------
After running ``provision.yml`` or ``discovery_provision.yml`` and the nodes boot up, additional NICs can be configured on target nodes using the ``nic_update.yml `` playbook.

**Prerequisites**

    * All target nodes are provisioned and booted. `Click here to verify the status of all nodes. <ViewingDB.html>`_

    * The ``input/network_spec.yml`` file has been updated with all network information including admin network and bmc network information.

    * The ``input/server_spec.yml`` file has been updated with all NIC information of the target nodes.

        * All NICs listed in the ``server_spec.yml`` file are grouped into categories (groups for servers). The string "Categories:" should not be edited out of the ``input/server_spec.yml`` file.
        * The property ``nicname`` is the unique identifier of NICs in the file.
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


Use the below commands to add the NICs: ::

    cd nic_update
    ansible-playbook nic_update/nic_update -i inventory

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

Based on the provided sample files, server 10.5.0.3 has been mapped to waco1 which corresponds to group-1. Therefore, the NICs ensp0 and ensp0.5 will be configured in an ethernet VLAN group with ens0.5 as the primary device.




