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
import shutil

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.discovery.standard_functions import (
    create_directory,
    render_template_multi_pass,
    load_vars_file
)

# pylint: disable=too-many-locals
def main():
    """
	Generates telemetry configuration for a list of service nodes.

    	Parameters:
		service_nodes_metadata (dict): A dictionary containing service node metadata.
		service_node_base_dir (str): The base directory for service nodes.
		file_permissions (str): The file permissions for the generated files.
		tmpl_telemetry (str): The path to the telemetry template.
		oim_shared_path (str): The path to the OIM shared path.
		vars_file (str): The path to the variables file (default: None).
		telemetry_vars_file (str): The path to the telemetry variables file (default: None).

	Returns:
		- A JSON object containing the results of processing each node,including the 
        changed status, a message describing the result, and the path to the written file.

    """

    # Define the module arguments
    module_args = {
        "service_nodes_metadata": {"type": "dict", "required": True},
        "service_node_base_dir": {"type": "str", "required": True},
        "file_permissions": {"type": "str", "required": True},
        "tmpl_telemetry": {"type": "str", "required": True},
        "oim_shared_path": {"type": "str", "required": True},
        "vars_file": {"type": "str", "required": False, "default": None},
        "telemetry_vars_file": {"type": "str", "required": False, "default": None}
    }

    # Create the Ansible module
    module = AnsibleModule(argument_spec=module_args)

    # Extract the module parameters
    service_nodes = module.params['service_nodes_metadata']
    base_dir = module.params['service_node_base_dir']
    file_mode = int(module.params['file_permissions'], 8)
    tmpl_telemetry = module.params['tmpl_telemetry']
    oim_shared_path = module.params['oim_shared_path']
    vars_file = module.params['vars_file']
    telemetry_vars_file = module.params['telemetry_vars_file']

    # Load the variables file
    extra_vars = load_vars_file(vars_file)
    telemetry_vars = load_vars_file(telemetry_vars_file)

    # Initialize the results list
    results = []
    passive_nodes = []

    # Process each node
    for _, node in service_nodes.items():
        # Skip nodes that are HA-enabled but not active
        if node.get('enable_service_ha') and not node.get('active'):
            continue

        # If telemetry is enabled and the node is active, collect its passive_node
        if node.get('enable_service_ha') and node.get('active'):
            passive_nodes.extend(node.get('passive_nodes'))

        # Extract the node parameters

        service_tag = node['service_tag']
        # service_node_name = node['hostname']
        service_admin_nic_ip = node['admin_ip']

        # # Create the node directories
        service_dir = os.path.join(base_dir, service_tag)
        pcs_dir = os.path.join(service_dir, 'pcs')
        pcs_config_dir = os.path.join(pcs_dir, 'config')
        pcs_telemetry_script_path = os.path.join(pcs_config_dir, 'pcs_telemetry.sh')

        # Create telemetry directories when idrac telemetry is supported
        # if module.params['idrac_telemetry_support'] == 'true':
        telemetry_dir = os.path.join(service_dir, 'telemetry')
        idrac_telemetry_dir = os.path.join(telemetry_dir, 'idrac_telemetry')
        activemq_dir = os.path.join(idrac_telemetry_dir, 'activemq')
        mysql_dir = os.path.join(idrac_telemetry_dir, 'mysqldb')
        idrac_telemetry_receiver_dir = os.path.join(idrac_telemetry_dir, 'idrac_telemetry_receiver')
        prometheus_dir = os.path.join(telemetry_dir, 'prometheus')
        prometheus_pump_dir = os.path.join(telemetry_dir, 'prometheus_pump')

        log_dir = os.path.join(service_dir, 'log')
        telemetry_log_dir = os.path.join(log_dir, 'telemetry')
        activemq_log = os.path.join(telemetry_log_dir, 'activemq')
        mysql_log = os.path.join(telemetry_log_dir, 'mysqldb')
        idrac_telemetry_receiver_log = os.path.join(telemetry_log_dir, 'idrac_telemetry_receiver')
        prometheus_log = os.path.join(telemetry_log_dir, 'prometheus')
        prometheus_pump_log = os.path.join(telemetry_log_dir, 'prometheus_pump')

        # Create the directories
        for path in [
            service_dir, pcs_dir, pcs_config_dir, telemetry_dir, idrac_telemetry_dir, activemq_dir, mysql_dir,
            idrac_telemetry_receiver_dir, prometheus_dir, prometheus_pump_dir,
            log_dir, telemetry_log_dir, activemq_log,
            mysql_log, idrac_telemetry_receiver_log, prometheus_log,
            prometheus_pump_log
        ]:
            create_directory(path, file_mode)


        # Create the template context
        context = {
            'service_tag': service_tag,
            'service_admin_nic_ip': service_admin_nic_ip,
            'oim_shared_path': oim_shared_path,
            **extra_vars,
            **telemetry_vars
        }

        # Render the telemetry templates
        render_template_multi_pass(tmpl_telemetry, pcs_telemetry_script_path, context, passes=5)

        os.chmod(pcs_telemetry_script_path, file_mode)

        # Add the result to the list
        results.append(f"Processed node {service_tag}")

        # Copy rendered active node directory to passive node directories
        for passive_service_tag in passive_nodes:
            passive_service_tag_dir = os.path.join(base_dir, passive_service_tag)

            if os.path.exists(passive_service_tag_dir):
                shutil.rmtree(passive_service_tag_dir)

            shutil.copytree(service_dir, passive_service_tag_dir)
            results.append(f"Copied config from active node: {service_tag} to passive node: {passive_service_tag}")

    # Exit the module
    module.exit_json(changed=True, msg="Nodes processed successfully", results=results)

if __name__ == '__main__':
    main()
