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
# pylint: disable=import-error,too-many-arguments,too-many-positional-arguments,wrong-import-position
"""
This module contains functions for validating function based on the file data.
"""
import sys

sys.path.append("module_utils/validation_flows")

from ansible.module_utils.input_validation.validation_flows import provision_validation
from ansible.module_utils.input_validation.validation_flows import common_validation
from ansible.module_utils.input_validation.validation_flows import high_availability_validation
from ansible.module_utils.input_validation.validation_flows import local_repo_validation
from ansible.module_utils.input_validation.validation_flows import build_stream_validation


# L2 Validation Code - validate anything that could not have been validated with JSON schema
# Main validation code that calls one of the validation functions based on the tag(s) used.
# input_file_inventory in validate_input.py contains dict of the tags being called.
def validate_input_logic(
    input_file_path,
    data,
    logger,
    module,
    omnia_base_dir,
    module_utils_base,
    project_name
):
    """
    Validates the input data based on the file name.

    Args:
        input_file_path (str): The path to the input file.
        data (dict): The data to be validated.
        logger (Logger): The logger object.
        module (AnsibleModule): The Ansible module object.
        omnia_base_dir (str): The base directory of Omnia.
        module_utils_base (str): The base directory of module_utils.
        project_name (str): The name of the project.

    Returns:
        list: A list of errors encountered during validation.
    """
    # Based on the file_name, run validation function
    validation_functions = {
        "provision_config.yml": provision_validation.validate_provision_config,
        "software_config.json": common_validation.validate_software_config,
        "network_spec.yml": provision_validation.validate_network_spec,
        "omnia_config.yml": common_validation.validate_omnia_config,
        "local_repo_config.yml": local_repo_validation.validate_local_repo_config,
        "telemetry_config.yml": common_validation.validate_telemetry_config,
        "security_config.yml": common_validation.validate_security_config,
        "storage_config.yml": common_validation.validate_storage_config,
        "high_availability_config.yml":
            high_availability_validation.validate_high_availability_config,
        "additional_software.json": common_validation.validate_additional_software,
        "build_stream_config.yml": build_stream_validation.validate_build_stream_config,
    }

    path_parts = input_file_path.split("/")
    file_name = path_parts[-1]

    validation_function = validation_functions.get(file_name, None)
    print("validation_function", validation_function)
    if validation_function:
        return validation_function(
            input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name
        )
    message = f"Unsupported file: {input_file_path, data}"
    logger.error(message)
