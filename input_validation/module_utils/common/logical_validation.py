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

import sys
sys.path.append("module_utils/validation_flows")

import provision_validation
import common_validation
import roles_validation

# L2 Validation Code - validate anything that could not have been validated with JSON schema
# Main validation code that calls one of the validation functions based on the tag(s) used. input_file_inventory in validate_input.py contains dict of the tags being called.
def validate_input_logic(input_file_path, data, logger, module, omnia_base_dir, project_name):
    # Based on the file_name, run validation function
    validation_functions = {
        "provision_config_credentials.yml": provision_validation.validate_provision_config_credentials,
        "provision_config.yml": provision_validation.validate_provision_config,
        "software_config.json": common_validation.validate_software_config,
        "network_spec.yml": provision_validation.validate_network_spec,
        "server_spec.yml": common_validation.validate_server_spec,
        "omnia_config.yml": common_validation.validate_omnia_config,
        "network_config.yml": common_validation.validate_network_config,
        "local_repo_config.yml": common_validation.validate_local_repo_config,
        "telemetry_config.yml": common_validation.validate_telemetry_config,
        "security_config.yml": common_validation.validate_security_config,
        "passwordless_ssh_config.yml": common_validation.validate_usernames,
        "k8s_access_config.yml": common_validation.validate_usernames,
        "roce_plugin_config.yml": common_validation.validate_roce_plugin_config,
        "storage_config.yml": common_validation.validate_storage_config,
        "login_node_security_config.yml": common_validation.validate_login_node_security_config,
        "site_config.yml": common_validation.validate_site_config,
        "roles_config.yml": roles_validation.validate_roles_config,
        "high_availability_config.yml": common_validation.validate_high_availability_config
    }
    
    path_parts = input_file_path.split("/")
    file_name = path_parts[-1]
    validation_function = validation_functions.get(file_name, None)
    print("validation_function", validation_function)
    if validation_function:
        return validation_function(
            input_file_path, data, logger, module, omnia_base_dir, project_name
        )
    else:
        message = f"Unsupported file: {input_file_path, data}"
        logger.error(message)