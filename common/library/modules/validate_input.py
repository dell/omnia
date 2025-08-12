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

"""
This module is used to validate input data.

It provides functions for verifying and validating input data, and also includes
functions for fetching and validating data.

Functions:
    validate_input
    get_data
    verify
"""

import logging
import os

# pylint: disable=no-name-in-module,E0401
import ansible.module_utils.input_validation.common_utils.data_fetch as fetch
import ansible.module_utils.input_validation.common_utils.data_validation as validate
import ansible.module_utils.input_validation.common_utils.data_verification as verify
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.input_validation.common_utils import config
from ansible.module_utils.input_validation.common_utils import en_us_validation_msg

def createlogger(project_name, tag_name=None):
    """
    Creates a logger object for the given project name and tag name.

    Args:
        project_name (str): The name of the project.
        tag_name (str, optional): The name of the tag. Defaults to None.

    Returns:
        logging.Logger: The logger object.
    """
    if tag_name:
        log_filename = f"{tag_name}_validation_omnia_{project_name}.log"
    else:
        log_filename = f"validation_omnia_{project_name}.log"

    log_file_path = os.path.join(config.INPUT_VALIDATOR_LOG_PATH, log_filename)
    logging.basicConfig(
        filename=log_file_path,
        format="%(asctime)s %(message)s",
        filemode="w"
    )
    logger = logging.getLogger(tag_name if tag_name else project_name)
    logger.setLevel(logging.DEBUG)
    return logger

def main():
    """
    The main function that runs the input validation.

    This function initializes the logger, verifies the existence of the specified directory,
    retrieves the list of JSON and YAML files, and sets up the schema and input data dictionaries.

    It then runs the validation for each file based on the specified tag names.
    The validation includes schema validation (L1) and logic validation (L2).
    """
    module_args = {
        "omnia_base_dir": {"type": "str", "required": True},
        "project_name": {"type": "str", "required": True},
        "tag_names": {"type": "list", "required": True},
        "module_utils_path": {"type": "str"}
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    
    module_utils_base = module.params["module_utils_path"]
    omnia_base_dir = module.params["omnia_base_dir"]
    project_name = module.params["project_name"]
    tag_names = module.params["tag_names"]

    schema_base_file_path = os.path.join(module_utils_base,'input_validation','schema')
    input_dir_path = os.path.join(omnia_base_dir, project_name)
    input_files = []

    input_file_inventory = config.input_file_inventory
    passwords_set = config.passwords_set
    extensions = config.extensions

    validation_status = {"tag": tag_names, "Passed": [], "Failed": []}
    vstatus = []

    logger = createlogger(project_name)

    # Start validation execution
    logger.info(en_us_validation_msg.get_header())

    # Check if the specified directory exists
    if not verify.directory_exists(input_dir_path, module, logger):
        error_message = f"The input directory {input_dir_path} does not exist."
        module.fail_json(msg=error_message)

    input_files = fetch.files_recursively(omnia_base_dir + "/" + project_name, extensions['json'])
    input_files = input_files + fetch.files_recursively(omnia_base_dir + "/" + project_name, extensions['yml'])

    input_file_dict = { fetch.file_name_from_path(file_path): file_path for file_path in input_files }

    if not input_files:
        error_message = f"yml and json files not found in directory: {input_dir_path}"
        logger.error(error_message)
        module.fail_json(msg=error_message)

    # Run L1 and L2 validation if user included a tag and extra var files.
    # Or user only had tags and no extra var files.
    for tag_name in tag_names:
        for name in input_file_inventory.get(tag_name, []):
            fname, _ = os.path.splitext(name)

            schema_file_path = schema_base_file_path + "/" + fname + extensions['json']

            if not verify.file_exists(schema_file_path, module, logger):
                error_message = (
                    f"The file schema: {fname}.json does not exist "
                    f"in directory: {schema_base_file_path}."
                )
                logger.info(error_message)
                module.fail_json(msg=error_message)

            input_file_path = input_file_dict.get(name)

            if input_file_path is None:
                error_message = (
                    f"file not found in directory: {omnia_base_dir}/{project_name}"
                )
                logger.error(error_message)
                module.fail_json(msg=error_message)

            # Validate the schema of the input file (L1)
            schema_status = validate.schema({
                                "input_file_path": input_file_path,
                                "schema_file_path": schema_file_path,
                                "passwords_set": passwords_set,
                                "omnia_base_dir": omnia_base_dir,
                                "project_name": project_name,
                                "logger": logger,
                                "module": module,
                            })

            # Validate the logic of the input file (L2) if L1 is success
            logic_status = False
            if schema_status:
                logic_status = validate.logic({
                            "input_file_path": input_file_path,
                            "module_utils_base": module_utils_base,
                            "omnia_base_dir": omnia_base_dir,
                            "project_name": project_name,
                            "logger": logger,
                            "module": module,
                        })

            # Append the validation status for the input file
            if (schema_status and logic_status):
                validation_status["Passed"].append(input_file_path)
            else:
                validation_status["Failed"].append(input_file_path)

            vstatus.append(schema_status)
            vstatus.append(logic_status)

    if not validation_status:
        message = "No validation has been performed. \
            Please provide tags or include individual file names."
        module.fail_json(msg=message)

    logger.error(en_us_validation_msg.get_footer())

    log_file_name = os.path.join(config.INPUT_VALIDATOR_LOG_PATH,
                                 f"validation_omnia_{project_name}.log")

    status_bool = all(vstatus)
    status_str = "completed" if status_bool else "failed"

    message = (f"Input validation {status_str} for: {project_name} input configuration(s)."
               f"Tag(s) run: {tag_names}. "
               f"Look at the logs for more details: filename={log_file_name}")

    module.exit_json(failed=not status_bool,
        msg=message,
        log_file_name=log_file_name,
        passed_files=list(set(validation_status['Passed'])),
        failed_files=list(set(validation_status['Failed']))
        )


if __name__ == "__main__":
    main()
