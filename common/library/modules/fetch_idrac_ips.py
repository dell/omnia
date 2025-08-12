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

#!/usr/bin/python
"""Module to map and fetch iDRAC IPs and related information from 
service cluster metadata and BMC group data. This module reads the
service cluster metadata and BMC group data to find iDRAC podnames
and their associated IPs. It checks for service tags and parent status
to filter relevant nodes, then retrieves the iDRAC podnames and IPs 
from the BMC group data. It compiles these details into a dictionary
where keys are iDRAC podnames and values are lists of IPs associated 
with those podnames.
The module also handles cases where no relevant data isfound"""

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
                    if 'oim' in parent_to_bmc_ip_details:
                        idrac_podname_ips[idrac_podname] = parent_to_bmc_ip_details['oim']

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
