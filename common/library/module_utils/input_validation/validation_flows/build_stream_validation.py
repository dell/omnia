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
# pylint: disable=import-error,no-name-in-module,too-many-positional-arguments,too-many-arguments,unused-argument
"""
Validates build stream configuration files for Omnia.
"""
from ansible.module_utils.input_validation.common_utils import validation_utils
from ansible.module_utils.input_validation.common_utils import config
from ansible.module_utils.input_validation.common_utils import en_us_validation_msg as msg

file_names = config.files
create_error_msg = validation_utils.create_error_msg
create_file_path = validation_utils.create_file_path


def validate_build_stream_config(input_file_path, data,
                                  logger, module, omnia_base_dir,
                                  module_utils_base, project_name):
    """
    Validates build stream configuration by checking enable_build_stream field.
    
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
    errors = []
    build_stream_yml = create_file_path(input_file_path, file_names["build_stream_config"])
    
    enable_build_stream = data.get("enable_build_stream")
    
    if enable_build_stream is None:
        errors.append(create_error_msg(build_stream_yml, "enable_build_stream", 
                                       msg.ENABLE_BUILD_STREAM_REQUIRED_MSG))
    elif not isinstance(enable_build_stream, bool):
        errors.append(create_error_msg(build_stream_yml, "enable_build_stream", 
                                       msg.ENABLE_BUILD_STREAM_BOOLEAN_MSG))
    
    return errors
