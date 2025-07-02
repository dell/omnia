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

"""Main L1 Validation code. Get the JSON schema and input file to validate"""

import json
import jsonschema
import ansible.module_utils.input_validation.common_utils.data_fetch as get
from ansible.module_utils.input_validation.common_utils import en_us_validation_msg
from ansible.module_utils.input_validation.common_utils import logical_validation


def schema(config):
    """
    Validates the input file against a JSON schema.

    Args:
        config: dict with keys:
        - input_file_path
        - schema_file_path
        - passwords_set
        - omnia_base_dir
        - project_name
        - logger
        - module

    Returns:
        bool: True if the validation is successful, False otherwise.
    """
    input_file_path = config["input_file_path"]
    schema_file_path = config["schema_file_path"]
    passwords_set = config["passwords_set"]
    omnia_base_dir = config["omnia_base_dir"]
    project_name = config["project_name"]
    logger = config["logger"]
    module = config["module"]
    try:
        input_data, extension = get.input_data(
            input_file_path, omnia_base_dir, project_name, logger, module
        )

        # If input_data is None, it means there was a YAML syntax error
        if input_data is None:
            return False

        # Load schema
        with open(schema_file_path, "r", encoding="utf-8") as schema_file:
            j_schema = json.load(schema_file)
        logger.debug(en_us_validation_msg.get_validation_initiated(input_file_path))

        validator = jsonschema.Draft7Validator(j_schema)
        errors = sorted(validator.iter_errors(input_data), key=lambda e: e.path)

        # if errors exist, then print an error with the line number
        if errors:
            for error in errors:
                error_path = ".".join(map(str, error.path))

                # Custom error messages for regex pattern failures
                if "Groups" == error_path:
                    error.message = en_us_validation_msg.INVALID_GROUP_NAME_MSG
                elif "location_id" in error_path:
                    error.message = en_us_validation_msg.INVALID_LOCATION_ID_MSG
                elif "ports" in error_path:
                    error.message = en_us_validation_msg.INVALID_SWITCH_PORTS_MSG
                # TODO: Add a syntax error message for roles
                # elif 'is not of type' in error.message:
                #     error.message = en_us_validation_msg.INVALID_ATTRIBUTES_ROLE_MSG
                error_msg = f"Validation Error at {error_path}: {error.message}"

                # For passwords, mask the value so that no password values are logged
                if error.path and error.path[-1] in passwords_set:
                    parts = error.message.split(" ", 1)
                    if parts:
                        parts[0] = f"'{'*' * (len(parts[0]) - 2)}'"
                    error_msg = f"Validation Error at {error_path}: {' '.join(parts)}"
                # For all other fields, just log the value
                logger.error(error_msg)

                # get the line number and log it
                line_number, is_line_num = None, False
                if "json" in extension:
                    line_number, is_line_num = get.json_line_number(
                        input_file_path, error_path, module
                    )
                elif "yml" in extension:
                    line_number, is_line_num = get.yml_line_number(
                        input_file_path, error_path, omnia_base_dir, project_name
                    )
                    logger.info(line_number, is_line_num)
                if line_number:
                    message = (
                        f"Error occurs on line {line_number}"
                        if is_line_num
                        else f"Error occurs on object or list entry on line {line_number}"
                    )
                    logger.error(message)
            logger.error(en_us_validation_msg.get_schema_failed(input_file_path))
            return False
        logger.info(en_us_validation_msg.get_schema_success(input_file_path))
        return True
    except jsonschema.exceptions.SchemaError as schemaerror:
        message = f"Internal schema validation error: {schemaerror.message}"
        logger.error(message)
        return False
    except ValueError as valueerror:
        message = f"Value error at {input_file_path}: {valueerror}"
        logger.error(message)
        return False
    except Exception as exception:
        message = f"An unexpected error occurred: {exception}"
        logger.error(message)
        return False


# Code to run the L2 validation validate_input_logic function.
def logic(config):
    """
    Validates the logic of the input file.

    Args:
    config: dict with keys:
        - input_file_path (str): The path to the input file.
        - omnia_base_dir (str): The base directory of Omnia.
        - module_utils_base (str): The base directory of the module utils.
        - project_name (str): The name of the project.
        - logger (logging.Logger): The logger object.
        - module (AnsibleModule): The Ansible module.

    Returns:
        bool: True if the logic validation is successful, False otherwise.

    Raises:
        ValueError: If a value error occurs.
        Exception: If an unexpected error occurs.
    """
    input_file_path = config["input_file_path"]
    omnia_base_dir = config["omnia_base_dir"]
    module_utils_base = config["module_utils_base"]
    project_name = config["project_name"]
    logger = config["logger"]
    module = config["module"]
    try:
        input_data, extension = get.input_data(
            input_file_path, omnia_base_dir, project_name, logger, module
        )

        errors = logical_validation.validate_input_logic(
            input_file_path,
            input_data,
            logger,
            module,
            omnia_base_dir,
            module_utils_base,
            project_name,
        )

        # Print errors, if the error value is None then send a separate message.
        # This is for values where it did not have a single key as the error
        if errors:
            for error in errors:
                error_msg = error.get("error_msg", "")
                error_key = error.get("error_key", "")
                error_value = error.get("error_value", "")

                logger.error(f"Validation Error at {error_key}: '{error_value}' {error_msg}")

                # log the line number based off of the input config file extension
                if "yml" in extension:
                    result = get.yml_line_number(
                        input_file_path, error_key, omnia_base_dir, project_name
                    )
                    if result is not None:
                        line_number, is_line_num = result
                        if line_number:
                            message = (
                                f"Error occurs on line {line_number}"
                                if is_line_num
                                else f"Error occurs on object or list on line {line_number}"
                            )
                            logger.error(message)
                elif "json" in extension:
                    result = get.json_line_number(input_file_path, error_key, module)
                    if result is not None:
                        line_number, is_line_num = result
                        if line_number:
                            message = (
                                f"Error occurs on line {line_number}"
                                if is_line_num
                                else f"Error occurs on object or list on line {line_number}"
                            )
                            logger.error(message)

            logger.error(en_us_validation_msg.get_logic_failed(input_file_path))
            return False
        logger.info(en_us_validation_msg.get_logic_success(input_file_path))
        return True
    except ValueError as valueerror:
        message = f"Value error at {input_file_path}: {valueerror}"
        logger.error(message, exc_info=True)
        return False
    except Exception as exception:
        message = f"An unexpected error occurred: {exception}"
        logger.error(message, exc_info=True)
        return False
