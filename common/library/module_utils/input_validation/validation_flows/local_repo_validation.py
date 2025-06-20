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
# pylint: disable=import-error,no-name-in-module,too-many-positional-arguments,too-many-arguments,unused-argument
"""
Validates local repository configuration files for Omnia.
"""
import json
from ansible.module_utils.input_validation.common_utils import validation_utils
from ansible.module_utils.input_validation.common_utils import config

file_names = config.files
create_error_msg = validation_utils.create_error_msg
create_file_path = validation_utils.create_file_path

# Below is a validation function for each file in the input folder
def validate_local_repo_config(input_file_path, data,
                               logger, module, omnia_base_dir,
                               module_utils_base, project_name):
    """
    Validates local repo configuration by checking cluster_os_type and
    omnia_repo_url_rhel fields are present and accessible.
    """
    # check to make sure associated os info is filled out
    #keeping this function for future if any additional check srequired
    errors = []
    software_config_file_path = create_file_path(input_file_path, file_names["software_config"])
    try:
        with open(software_config_file_path, "r", encoding="utf-8") as f:
            software_config_json = json.load(f)
    except json.JSONDecodeError as jsonerror:
        errors.append(create_error_msg("Error opening or reading JSON file:",
                                        software_config_file_path, str(jsonerror)))
    except FileNotFoundError as fileerror:
        errors.append(create_error_msg("File not found.",
                                        software_config_file_path, str(fileerror)))
    return errors
