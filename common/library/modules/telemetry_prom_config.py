# Copyright 2025 Dell Inc. or its subsidiaries. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

#!/usr/bin/python

"""This module provides functionality for telemetry PCS nodes."""

# pylint: disable=import-error,no-name-in-module,line-too-long

import os
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.discovery.standard_functions import render_template

# pylint: disable=too-many-locals
def main():
    """
	Generates telemetry configuration for a list of service nodes.

	Parameters:
		service_nodes_metadata (dict): A dictionary containing service node metadata.
		service_node_base_dir (str): The base directory where the service nodes will be created.
		file_permissions (str): The file permissions for the generated files.
		tmpl_telemetry (str): The path to the telemetry template.

	Returns:
		A JSON object with the results of processing each node, including the changed status, a message describing the result, and the path to the written file.
	"""
    # Define the module arguments
    module_args = {
        "service_nodes_metadata": {"type": "dict", "required": True},
        "service_node_base_dir": {"type": "str", "required": True},
        "file_permissions": {"type": "str", "required": True},
        "tmpl_telemetry": {"type": "str", "required": True}
    }

    # Create the Ansible module
    module = AnsibleModule(argument_spec=module_args)

    # Extract the module parameters
    service_nodes = module.params['service_nodes_metadata']
    base_dir = module.params['service_node_base_dir']
    file_mode = int(module.params['file_permissions'], 8)
    tmpl_telemetry = module.params['tmpl_telemetry']

    # Initialize the results list
    results = []

    # Process each node
    for _, node in service_nodes.items():
        if node.get('enable_service_ha') and not node.get('active'):
            continue
        service_tag = node['service_tag']
        # service_node_name = node['hostname']
        service_active_nic_ip = node['virtual_ip_address'] if node.get('enable_service_ha') else node[' admin_ip']

        # # Create the node directories
        service_dir = os.path.join(base_dir, service_tag)
        telemetry_dir = os.path.join(service_dir, 'telemetry')
        prometheus_dir = os.path.join(telemetry_dir, 'prometheus')
        prometheus_config_file_path = os.path.join(prometheus_dir, 'prometheus.yml')

        # Create the template context
        context = {
            'service_tag': service_tag,
            'service_active_nic_ip': service_active_nic_ip
        }

        # Render the telemetry templates
        render_template(tmpl_telemetry, prometheus_config_file_path, context)

        os.chmod(prometheus_config_file_path, file_mode)

        # Add the result to the list
        results.append(f"PPrometheus config generated for {service_tag}")

    # Exit the module
    module.exit_json(changed=True, msg="Prometheus config generated successfully", results=results)

if __name__ == '__main__':
    main()
