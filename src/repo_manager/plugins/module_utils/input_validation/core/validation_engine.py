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
# pylint: disable=import-error,no-name-in-module,too-many-locals,too-many-branches
# pylint: disable=too-many-statements,broad-exception-caught,too-many-arguments
# pylint: disable=too-many-positional-arguments,import-outside-toplevel,too-many-nested-blocks
# pylint: disable=line-too-long
"""
Validation Engine - Core validation orchestration.

This module provides the main entry points for:
- L1 Validation: JSON Schema validation
- L2 Validation: Business logic validation

It orchestrates the validation process and routes to appropriate validators.
"""
import json
import jsonschema

from ansible.module_utils.input_validation.core import file_utils
from ansible.module_utils.input_validation.messages import common_messages as msg


def schema(config):
    """
    Validates the input file against a JSON schema (L1 Validation).

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
        list: List of error messages, empty if validation passed.
    """
    input_file_path = config["input_file_path"]
    schema_file_path = config["schema_file_path"]
    passwords_set = config["passwords_set"]
    omnia_base_dir = config["omnia_base_dir"]
    project_name = config["project_name"]
    logger = config["logger"]
    module = config["module"]
    error_bucket = []

    try:
        input_data, extension = file_utils.input_data(
            input_file_path, omnia_base_dir, project_name, logger, module
        )

        if input_data is None:
            error_bucket.append("input data reading failed.")
            return error_bucket

        # Normalize case-sensitive fields for omnia_config.yml
        if "omnia_config" in input_file_path:
            if "slurm_cluster" in input_data:
                for cluster in input_data["slurm_cluster"]:
                    if "node_discovery_mode" in cluster and isinstance(cluster["node_discovery_mode"], str):
                        cluster["node_discovery_mode"] = cluster["node_discovery_mode"].lower()

        # Load schema
        with open(schema_file_path, "r", encoding="utf-8") as schema_file:
            j_schema = json.load(schema_file)

        logger.debug(msg.get_validation_initiated(input_file_path))

        validator = jsonschema.Draft7Validator(
            j_schema, format_checker=jsonschema.Draft7Validator.FORMAT_CHECKER
        )
        errors = sorted(validator.iter_errors(input_data), key=lambda e: e.path)

        if errors:
            for error in errors:
                error_path = ".".join(map(str, error.path))

                # Custom error messages for regex pattern failures
                if "groups" == error_path:
                    error.message = msg.INVALID_GROUP_NAME_MSG
                elif "ports" in error_path:
                    error.message = msg.INVALID_SWITCH_PORTS_MSG

                error_msg = f"Validation Error at {error_path}: {error.message}"

                # Mask password values
                if error.path and error.path[-1] in passwords_set:
                    parts = error.message.split(" ", 1)
                    if parts:
                        masked = "*" * (len(parts[0]) - 2)
                        parts[0] = f"'{masked}'"
                    error_msg = f"Validation Error at {error_path}: {' '.join(parts)}"

                logger.error(error_msg)
                error_bucket.append(error_msg)

                # Get line number
                line_number, is_line_num = None, False
                if "json" in extension:
                    line_number, is_line_num = file_utils.json_line_number(
                        input_file_path, error_path, module
                    )
                elif "yml" in extension:
                    line_number, is_line_num = file_utils.yml_line_number(
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
                    error_bucket.append(message)

            logger.error(msg.get_schema_failed(input_file_path))
            error_bucket.append(msg.get_schema_failed(input_file_path))

    except jsonschema.exceptions.SchemaError as schemaerror:
        message = f"Internal schema validation error: {schemaerror.message}"
        logger.error(message)
        error_bucket.append(message)
    except ValueError as valueerror:
        message = f"Value error at {input_file_path}: {valueerror}"
        logger.error(message)
        error_bucket.append(message)
    except Exception as exception:
        message = f"An unexpected error occurred: {exception}"
        logger.error(message)
        error_bucket.append(message)

    logger.info(msg.get_schema_success(input_file_path))
    return error_bucket


def logic(config):
    """
    Validates the logic of the input file (L2 Validation).

    Args:
        config: dict with keys:
            - input_file_path
            - omnia_base_dir
            - module_utils_base
            - project_name
            - logger
            - module

    Returns:
        list: List of error messages, empty if validation passed.
    """
    input_file_path = config["input_file_path"]
    omnia_base_dir = config["omnia_base_dir"]
    module_utils_base = config["module_utils_base"]
    project_name = config["project_name"]
    logger = config["logger"]
    module = config["module"]
    error_bucket = []

    try:
        input_data, extension = file_utils.input_data(
            input_file_path, omnia_base_dir, project_name, logger, module
        )

        errors = validate_input_logic(
            input_file_path,
            input_data,
            logger,
            module,
            omnia_base_dir,
            module_utils_base,
            project_name,
        )

        if errors:
            for error in errors:
                error_msg = error.get("error_msg", "")
                error_key = error.get("error_key", "")
                error_value = error.get("error_value", "")

                err_msg = f"Validation Error at {error_key}: '{error_value}' {error_msg}"
                error_bucket.append(err_msg)
                logger.error(err_msg)

                # Log line number
                if "yml" in extension:
                    result = file_utils.yml_line_number(
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
                    result = file_utils.json_line_number(input_file_path, error_key, module)
                    if result is not None:
                        line_number, is_line_num = result
                        if line_number:
                            message = (
                                f"Error occurs on line {line_number}"
                                if is_line_num
                                else f"Error occurs on object or list on line {line_number}"
                            )
                            logger.error(message)

            logger.error(msg.get_logic_failed(input_file_path))
            return error_bucket

    except ValueError as valueerror:
        message = f"Value error at {input_file_path}: {valueerror}"
        error_bucket.append(message)
        logger.error(message, exc_info=True)
        return error_bucket
    except Exception as exception:
        message = f"An unexpected error occurred: {exception}"
        error_bucket.append(message)
        logger.error(message, exc_info=True)
        return error_bucket

    logger.info(msg.get_logic_success(input_file_path))
    return False


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
    Routes validation to the appropriate validator based on file name.

    Args:
        input_file_path (str): The path to the input file.
        data (dict): The data to be validated.
        logger: Logger instance.
        module: Ansible module instance.
        omnia_base_dir (str): The base directory of Omnia.
        module_utils_base (str): The base directory of module_utils.
        project_name (str): The name of the project.

    Returns:
        list: A list of errors encountered during validation.
    """
    # Import validators here to avoid circular imports
    from ansible.module_utils.input_validation.validators import repo_manager_config

    validation_functions = {
        "repo_manager_config.yml": repo_manager_config.validate,
    }

    path_parts = input_file_path.split("/")
    file_name = path_parts[-1]

    validation_function = validation_functions.get(file_name, None)
    print("validation_function", validation_function)

    if validation_function:
        return validation_function(
            input_file_path,
            data,
            logger,
            module,
            omnia_base_dir,
            module_utils_base,
            project_name
        )

    return []
