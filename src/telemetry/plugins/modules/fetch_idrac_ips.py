# Copyright 2025 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=import-error,no-name-in-module,line-too-long

#!/usr/bin/python
"""Module to map and fetch iDRAC IPs and related information from
service cluster metadata and BMC group data."""

DOCUMENTATION = r'''
---
module: fetch_idrac_ips
short_description: Map iDRAC pod names to their associated BMC IPs
version_added: "2.3.0"
description:
  - Reads service cluster metadata and BMC group data to build a mapping
    of iDRAC pod names to their associated BMC IP addresses.
  - Filters nodes by C(service_tag) presence and C(parent_status) flag,
    then cross-references with the BMC group data dictionary.
  - Management nodes (role C(service_kube_control_plane)) are mapped to
    the C(MGMT_node) key in the BMC group data.
options:
  service_cluster_metadata:
    description: >
      Dictionary of service cluster node metadata keyed by node identifier.
      Each entry should contain C(service_tag), C(parent_status),
      C(idrac_podname), and optionally C(role).
    type: dict
    required: true
  parent_to_bmc_ip_details:
    description: >
      Dictionary mapping parent service tags to lists of BMC IP addresses.
      Should include a C(MGMT_node) key for management node IPs.
    type: dict
    required: true
author:
  - Dell Technologies (@dell)
'''

EXAMPLES = r'''
- name: Fetch iDRAC pod-to-IP mapping
  omnia.telemetry.fetch_idrac_ips:
    service_cluster_metadata: "{{ service_cluster_metadata }}"
    parent_to_bmc_ip_details: "{{ parent_to_bmc_ip_details }}"
  register: idrac_result

- name: Display the mapping
  ansible.builtin.debug:
    var: idrac_result.idrac_podname_ips
'''

RETURN = r'''
changed:
  description: Always false (read-only module).
  type: bool
  returned: always
  sample: false
idrac_podname_ips:
  description: >
    Dictionary mapping iDRAC pod names to lists of BMC IP addresses
    associated with that pod.
  type: dict
  returned: always
  sample:
    idrac-pod-0: ["192.168.1.10", "192.168.1.11"]
    idrac-pod-1: ["192.168.1.20"]
'''

from ansible.module_utils.basic import AnsibleModule

def fetch_pod_to_idracips(service_cluster_metadata, parent_to_bmc_ip_details, module):
    """
    Maps iDRAC podnames to their associated IPs using service cluster metadata and BMC group data.
    Returns a dictionary where keys are iDRAC podnames and values are lists of IPs.
    """
    idrac_podname_ips = {}

    for node in service_cluster_metadata.values():
        if node.get("service_tag") and node.get("parent_status") is True:
            idrac_podname = node.get("idrac_podname")
            target_tag = node.get("service_tag")

            if not idrac_podname or not target_tag:
                module.warn("Missing idrac_podname or service_tag in service nodes metadata.")
                continue

            if target_tag in parent_to_bmc_ip_details:
                bmc_group_data_list = parent_to_bmc_ip_details.get(target_tag, [])
                if not bmc_group_data_list:
                    module.warn(f"No BMC group data found for service tag {target_tag}.")
                else:
                    module.warn(f"Found BMC group data for service tag \
                    {target_tag}: {bmc_group_data_list}")
                    idrac_podname_ips[idrac_podname] = bmc_group_data_list
            else:
                role_string = node.get("role", "")
                roles = [r.strip() for r in role_string.split(",")]
                if "service_kube_control_plane" in roles:
                    if 'MGMT_node' in parent_to_bmc_ip_details:
                        idrac_podname_ips[idrac_podname] = parent_to_bmc_ip_details['MGMT_node']

    if not idrac_podname_ips:
        module.warn("No iDRAC podnames and IPs found in the service cluster metadata.")

    return idrac_podname_ips

def main():
    """Main function to execute the module logic."""
    # Define the module arguments
    # service_cluster_metadata: Metadata about the service cluster
    # parent_to_bmc_ip_details: Mapping of service tags to BMC group data
    # This module expects these inputs to be provided by the playbook
    # or task that calls this module.
    # It will process these inputs to find iDRAC podnames and their IPs.
    # The output will be a dictionary where keys are iDRAC podnames and
    # values are lists of IPs associated with those podnames.
    module_args = {
        "service_cluster_metadata": {"type":"dict", "required":True},
        "parent_to_bmc_ip_details": {"type":"dict", "required":True}
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    try:
        service_cluster_metadata = module.params["service_cluster_metadata"]
        module.warn(f"Service Cluster metadata path: {service_cluster_metadata}")
        parent_to_bmc_ip_details = module.params["parent_to_bmc_ip_details"]

        if not service_cluster_metadata:
            module.warn("Service cluster metadata is required but not provided.")
        if not parent_to_bmc_ip_details:
            module.warn("BMC group data list is required but not provided.")

        idrac_podname_ips = fetch_pod_to_idracips(service_cluster_metadata, \
                        parent_to_bmc_ip_details, module)

        module.exit_json(
            changed=False,
            idrac_podname_ips=idrac_podname_ips
        )
    except Exception as e:
        module.fail_json(
            msg=f"An error occurred while fetching iDRAC podnames and IPs: {str(e)}"
        )

if __name__ == "__main__":
    main()
