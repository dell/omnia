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
from configparser import ConfigParser
# pylint: disable=no-name-in-module,E0401
import ansible.module_utils.input_validation.common_utils.data_fetch as get
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

    log_file_path = os.path.join(config.input_validator_log_path, log_filename)
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

    The function also handles exceptions and logs the validation status.

    Parameters:
        None

    Returns:
        None

    Raises:
        FileNotFoundError: If the specified directory or schema file does not exist.
        ValueError: If there is a value error.
        Exception: If there is an unexpected error.
    """
    module_args = dict(
        omnia_base_dir=dict(type="str", required=True),
        project_name=dict(type="str", required=True),
        tag_names=dict(type="str", required=True),
        files=dict(type="list", elements="str", required=False),
        module_utils_path=dict(type="str", required=False, default=None)
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    module_utils_base = module.params["module_utils_path"]
    omnia_base_dir = module.params["omnia_base_dir"]
    project_name = module.params["project_name"]
    tag_names = eval(module.params["tag_names"])
    single_files = module.params["files"]
    schema_base_file_path = os.path.join(module_utils_base,'input_validation','schema')
    directory_path = os.path.join(omnia_base_dir, project_name)
    input_file_inventory = config.input_file_inventory
    passwords_set = config.passwords_set
    extensions = config.extensions

    json_files_dic = {}
    yml_files_dic = {}
    schema_files_dic = {}
    validation_status = {}
    vstatus = []

    logger = createlogger(project_name)

    # Start validation execution
    logger.info(en_us_validation_msg.get_header())

    # Check if the specified directory exists
    if not verify.directory_exists(directory_path, module, logger):
        error_message = f"The directory {directory_path} does not exist."
        logger.info(error_message)
        raise FileNotFoundError(error_message)

    json_files = get.files_recursively(omnia_base_dir + "/" + project_name, extensions['json'])
    yml_files = get.files_recursively(omnia_base_dir + "/" + project_name, extensions['yml'])
    schema_files = get.files_recursively(schema_base_file_path, extensions['json'])

    for file_path in json_files:
        json_files_dic.update({get.file_name_from_path(file_path): file_path})
    for file_path in yml_files:
        yml_files_dic.update({get.file_name_from_path(file_path): file_path})
    for file_path in schema_files:
        schema_files_dic.update({get.file_name_from_path(file_path): file_path})

    if not json_files and not yml_files:
        error_message = f"yml and json files not found in directory: {directory_path}"
        logger.error(error_message)
        module.fail_json(msg=error_message)
        raise FileNotFoundError(error_message)

    # For each file from the tag names, run schema validation (L1) and logic validation (L2)
    project_data = {project_name: {"status": [], "tag": tag_names}}

    if len(single_files) > 0:
        for name in single_files:
            if not name:
                continue
            validation_status.update(project_data)
            fname = os.path.splitext(name)[0]
            schema_file_path = schema_base_file_path + "/" + fname + extensions['json']
            logger.info(f"schema_file_path: {schema_file_path}")
            input_file_path = None

            if not verify.file_exists(schema_file_path, module, logger):
                error_message = f"The file schema: {fname}.json does not exist in directory: \
                    {schema_base_file_path}."
                logger.info(error_message)
                module.fail_json(msg=error_message)
                raise FileNotFoundError(error_message)
            if name in json_files_dic.keys():
                input_file_path = json_files_dic[name]
            if name in yml_files_dic.keys():
                input_file_path = yml_files_dic[name]

            if input_file_path is None:
                error_message = f"file not found in directory: {omnia_base_dir}/{project_name}"
                logger.error(error_message)
                module.fail_json(msg=error_message)
                raise FileNotFoundError(error_message)

            # Validate the schema of the input file (L1)
            schema_status = validate.schema(input_file_path, schema_file_path, passwords_set, \
                                            omnia_base_dir, project_name, logger, module)
            # Append the validation status for the input file
            validation_status[project_name]["status"].append(
                {input_file_path: "Passed" if schema_status else "Failed"})
            if len(tag_names) == 0:
                validation_status[project_name]["tag"] = ['none']

            vstatus.append(schema_status)
    # Run L1 and L2 validation if user included a tag and extra var files.
    # Or user only had tags and no extra var files.
    if (len(tag_names) > 0 and "all" not in tag_names and len(single_files) > 0) or \
        (len(tag_names) > 0 and len(single_files) == 0):
        for tag_name in tag_names:
            if tag_name in input_file_inventory and input_file_inventory[tag_name]:
                for name in input_file_inventory[tag_name]:
                    validation_status.update(project_data)
                    fname, _ = os.path.splitext(name)
                    schema_file_path = schema_base_file_path + "/" + fname + extensions['json']
                    input_file_path = None

                    if not verify.file_exists(schema_file_path, module, logger):
                        error_message = f"The file schema: {fname}.json does not exist in directory: \
                            {schema_base_file_path}."
                        logger.info(error_message)
                        module.fail_json(msg=error_message)
                        raise FileNotFoundError(error_message)

                    if name in json_files_dic.keys():
                        input_file_path = json_files_dic[name]
                    if name in yml_files_dic.keys():
                        input_file_path = yml_files_dic[name]

                    if input_file_path is None:
                        error_message = f"file not found in directory: {omnia_base_dir}/{project_name}"
                        logger.error(error_message)
                        module.fail_json(msg=error_message)
                        raise FileNotFoundError(error_message)

                    # Validate the schema of the input file (L1)
                    schema_status = validate.schema(input_file_path, schema_file_path, passwords_set, \
                                                    omnia_base_dir, project_name, logger, module)

                    # Validate the logic of the input file (L2) if L1 is success
                    logic_status = (
                        validate.logic(input_file_path, logger, module, omnia_base_dir, \
                                                    module_utils_base, project_name)
                    ) if schema_status else False

                    # Append the validation status for the input file
                    validation_status[project_name]["status"].append({input_file_path: "Passed" \
                        if (schema_status and logic_status) else "Failed"})

                    # vstatus contains boolean values.If False exists,
                    # that means validation failed and the module will result in failure
                    vstatus.append(schema_status)
                    vstatus.append(logic_status)

    if not validation_status:
        message = "No validation has been performed. \
            Please provide tags or include individual file names."
        module.fail_json(msg=message)
    validation_status[project_name]["status"].sort(key=lambda x: list(x.values())[0])

    logger.error(en_us_validation_msg.get_footer())

    log_file_name = os.path.join(config.input_validator_log_path, f"validation_omnia_{project_name}.log")

    # Ansible success/failure message
    if False in vstatus:
        status = validation_status[project_name]['status']
        tag = validation_status[project_name]['tag']
        failed_files = [file for item in status for file, result in item.items() \
                        if result == 'Failed']
        passed_files = [file.split("/")[-1] for item in status for file, result in item.items() \
                        if result == 'Passed']
        message = (
            f"Input validation failed for: {failed_files} input configuration(s). \
                Validation passed for {passed_files}. "
            f"Tag(s) run: {tag}. Look at the logs for more details: \
                filename={log_file_name}"
            )
        module.fail_json(msg=message)
    else:
        message = f"Input validation completed for project: {validation_status} input configs. \
            Look at the logs for more details: filename={log_file_name}"
        module.exit_json(msg=message)


if __name__ == "__main__":
    main()
