# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
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
Telemetry-specific L2 logic validation dispatcher.
Standalone version — dispatches only to telemetry validation functions.
"""
import sys

sys.path.append("module_utils/validation_flows")

from ansible.module_utils.input_validation.validation_flows import telemetry_validation


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
    Dispatches L2 validation to the appropriate telemetry validation function
    based on the input file name.

    Args:
        input_file_path (str): The path to the input file.
        data (dict): The parsed YAML data to validate.
        logger (Logger): The logger object.
        module (AnsibleModule): The Ansible module object.
        omnia_base_dir (str): The base directory of Omnia.
        module_utils_base (str): The base directory of module_utils.
        project_name (str): The name of the project.

    Returns:
        list: A list of errors encountered during validation.
    """
    validation_functions = {
        "telemetry_config.yml": telemetry_validation.validate_telemetry_config,
        "telemetry_storage_config.yml": telemetry_validation.validate_telemetry_storage_config,
        "telemetry_packages.yml": telemetry_validation.validate_telemetry_packages,
    }

    path_parts = input_file_path.split("/")
    file_name = path_parts[-1]

    validation_function = validation_functions.get(file_name, None)
    if validation_function:
        return validation_function(
            input_file_path, data, logger, module, omnia_base_dir, module_utils_base, project_name
        )
    message = f"Unsupported telemetry input file: {input_file_path}"
    logger.error(message)
    return []
