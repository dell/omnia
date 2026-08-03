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

#!/usr/bin/python

"""
Input Validation Module for Ansible.

This module validates input configuration files using:
- L1 Validation: JSON Schema validation
- L2 Validation: Business logic validation

Usage:
    validate_input:
        omnia_base_dir: /path/to/omnia
        project_name: input
        tag_names: [local_repo]
        module_utils_path: /path/to/module_utils
"""

import logging
import os
import csv

from ansible.module_utils.basic import AnsibleModule
DOCUMENTATION = r"""
---
module: validate_input
short_description: Validate input configuration files
description:
  - This module validates input configuration files against schemas.
  - It performs comprehensive validation of repo_manager configuration.
version_added: "1.0.0"
options:
    config_path:
      description: Path to configuration file
      required: true
      type: str
    schema_path:
      description: Path to JSON schema file
      required: false
      type: str
    strict:
      description: Enable strict validation mode
      required: false
      type: bool
      default: True

author:
  - Dell Technologies (@dell)
"""

EXAMPLES = r"""
- name: Validate repo_manager configuration
  validate_input:
    config_path: /opt/omnia/input/repo_manager_config.yml
    strict: true
  register: validation_result
"""

RETURN = r"""
valid:
  description: Whether configuration is valid
  type: bool
  returned: always
errors:
  description: List of validation errors
  type: list
  returned: on_error
warnings:
  description: List of validation warnings
  type: list
  returned: always
"""




def validate_csv_structure(csv_file_path, logger=None):
    """
    Validate CSV structure for PXE mapping files.

    Args:
        csv_file_path (str): Path to the CSV file to validate
        logger: Logger instance for logging

    Returns:
        bool: True if validation passes

    Raises:
        ValueError: If CSV structure validation fails
    """
    try:
        if not os.path.exists(csv_file_path):
            error_msg = f"CSV ERROR: File not found - {csv_file_path}"
            if logger:
                logger.error(error_msg)
            raise ValueError(error_msg)

        with open(csv_file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
            except StopIteration:
                error_msg = f"CSV ERROR: Empty file - {csv_file_path}"
                if logger:
                    logger.error(error_msg)
                raise ValueError(error_msg)

            expected_columns = len(header)
            line_num = 2

            for row in reader:
                if len(row) != expected_columns:
                    error_msg = (
                        f"CSV ERROR: {csv_file_path}: Line {line_num} has {len(row)} columns, "
                        f"expected {expected_columns}. Missing values in CSV row. "
                        f"Ensure each row has the correct number of values separated by commas."
                    )
                    if logger:
                        logger.error(error_msg)
                        logger.error(f"Problem row: {','.join(row)}")
                    raise ValueError(error_msg)
                line_num += 1

        success_msg = f"CSV validation passed - {line_num - 2} rows validated"
        if logger:
            logger.info(success_msg)
        print(success_msg)
        return True

    except Exception as e:
        error_msg = f"CSV validation error: {str(e)}"
        if logger:
            logger.error(error_msg)
        raise ValueError(error_msg)


def createlogger(project_name, tag_name=None):
    """
    Creates a logger object for the given project name and tag name.

    Args:
        project_name (str): The name of the project.
        tag_name (str, optional): The name of the tag.

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
    Main function that runs the input validation.

    This function:
    1. Initializes the logger
    2. Verifies the existence of the specified directory
    3. Retrieves the list of JSON and YAML files
    4. Runs L1 (schema) and L2 (logic) validation for each file
    """
    module_args = {
        "omnia_base_dir": {"type": "str", "required": True},
        "project_name": {"type": "str", "required": True},
        "input_project_dir": {"type": "str", "required": False},
        "tag_names": {"type": "list", "required": True},
        "module_utils_path": {"type": "str"},
        "csv_file_path": {"type": "str", "required": False},
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    module_utils_base = module.params["module_utils_path"]
    omnia_base_dir = module.params["omnia_base_dir"]
    project_name = module.params["project_name"]
    input_project_dir = module.params.get("input_project_dir", "")
    tag_names = module.params["tag_names"]
    csv_file_path = module.params.get("csv_file_path", "")

    # Set base directory environment variable before importing config modules
    if "REPO_MANAGER_BASE_DIR" not in os.environ:
        os.environ["REPO_MANAGER_BASE_DIR"] = os.path.dirname(os.path.normpath(omnia_base_dir))

    # Import modules after setting environment variable
    # pylint: disable=no-name-in-module,E0401
    global config, file_utils, validation_engine, msg

    # Import from new reorganized structure
    from ansible.module_utils.input_validation.core import config
    from ansible.module_utils.input_validation.core import file_utils
    from ansible.module_utils.input_validation.core import validation_engine
    from ansible.module_utils.input_validation.messages import common_messages as msg

    schema_base_file_path = os.path.join(module_utils_base, 'input_validation', 'schema')
    if input_project_dir:
        input_dir_path = input_project_dir
        # Derive omnia_base_dir and project_name for any legacy consumers
        omnia_base_dir = os.path.dirname(input_dir_path)
        project_name = os.path.basename(input_dir_path)
    else:
        input_dir_path = os.path.join(omnia_base_dir, project_name)
    input_files = []

    input_file_inventory = config.input_file_inventory
    passwords_set = config.passwords_set
    extensions = config.extensions

    validation_status = {"tag": tag_names, "Passed": [], "Failed": []}
    vstatus = []

    logger = createlogger(project_name)

    # Start validation execution
    logger.info(msg.get_header())

    # Check if the specified directory exists
    if not file_utils.directory_exists(input_dir_path, module, logger):
        error_message = f"The input directory {input_dir_path} does not exist."
        module.fail_json(msg=error_message)

    input_files = file_utils.files_recursively(omnia_base_dir + "/" + project_name, extensions['json'])
    input_files = input_files + file_utils.files_recursively(omnia_base_dir + "/" + project_name, extensions['yml'])

    input_file_dict = {file_utils.file_name_from_path(file_path): file_path for file_path in input_files}

    if not input_files:
        error_message = f"yml and json files not found in directory: {input_dir_path}"
        logger.error(error_message)
        module.fail_json(msg=error_message)

    # Run L1 and L2 validation
    error_bucket = []

    # Check if build_stream is enabled to determine if GitLab validation should run
    skip_gitlab_validation = False
    build_stream_config_path = os.path.join(omnia_base_dir, project_name, "build_stream_config.yml")
    if os.path.exists(build_stream_config_path):
        try:
            build_stream_data, _ = file_utils.input_data(
                build_stream_config_path, omnia_base_dir, project_name, logger, module
            )
            if build_stream_data:
                enable_build_stream = build_stream_data.get("enable_build_stream", False)
                if not enable_build_stream:
                    skip_gitlab_validation = True
                    logger.info("build_stream is disabled, skipping gitlab_config.yml validation")
        except Exception:
            logger.warning("Failed to check build_stream status from build_stream_config.yml")

    for tag_name in tag_names:
        for name in input_file_inventory.get(tag_name, []):
            fname, _ = os.path.splitext(name)

            schema_file_path = schema_base_file_path + "/" + fname + extensions['json']

            if not file_utils.file_exists(schema_file_path, module, logger):
                error_message = (
                    f"The file schema: {fname}.json does not exist "
                    f"in directory: {schema_base_file_path}."
                )
                logger.info(error_message)
                module.fail_json(msg=error_message)

            input_file_path = input_file_dict.get(name)

            # Skip gitlab_config.yml validation if build_stream is disabled
            if skip_gitlab_validation and name == "gitlab_config.yml":
                logger.info("Skipping gitlab_config.yml validation (build_stream disabled)")
                continue

            if input_file_path is None:
                error_message = (
                    f"{fname} file not found in directory: {omnia_base_dir}/{project_name}"
                )
                logger.error(error_message)
                module.fail_json(msg=error_message)

            # L1 Validation: Schema validation
            l1_errors = validation_engine.schema({
                "input_file_path": input_file_path,
                "schema_file_path": schema_file_path,
                "passwords_set": passwords_set,
                "omnia_base_dir": omnia_base_dir,
                "project_name": project_name,
                "logger": logger,
                "module": module,
            })

            if l1_errors:
                error_bucket = error_bucket + l1_errors
                schema_status = False
            else:
                schema_status = True

            # L2 Validation: Logic validation (only if L1 passed)
            logic_status = True
            if schema_status:
                l2_errors = validation_engine.logic({
                    "input_file_path": input_file_path,
                    "module_utils_base": module_utils_base,
                    "omnia_base_dir": omnia_base_dir,
                    "project_name": project_name,
                    "logger": logger,
                    "module": module,
                })
                if l2_errors:
                    error_bucket = error_bucket + l2_errors
                    logic_status = False
                else:
                    logic_status = True

            # Append the validation status
            if schema_status and logic_status:
                validation_status["Passed"].append(input_file_path)
            else:
                validation_status["Failed"].append(input_file_path)

            vstatus.append(schema_status)
            vstatus.append(logic_status)

    # Optional CSV validation
    if csv_file_path:
        try:
            validate_csv_structure(csv_file_path, logger)
            validation_status["tag"].append("csv_structure")
            vstatus.append(True)
        except ValueError as csv_error:
            error_bucket = error_bucket + [str(csv_error)]
            validation_status["Failed"].append(csv_file_path)
            vstatus.append(False)

    if not validation_status:
        message = (
            "No validation has been performed. "
            "Please provide tags or include individual file names."
        )
        module.fail_json(msg=message)

    logger.error(msg.get_footer())

    log_file_name = os.path.join(
        config.INPUT_VALIDATOR_LOG_PATH,
        f"validation_omnia_{project_name}.log"
    )

    status_bool = all(vstatus)
    status_str = "completed" if status_bool else "failed"

    message = [
        f"Input validation {status_str} for: {project_name} input configuration(s).",
        f"Tag(s) run: {tag_names}. ",
        f"Look at the logs for more details: filename={log_file_name}"
    ]

    module.exit_json(
        changed=False,
        validation_failed=not status_bool,
        error_msg=message,
        log_file=log_file_name,
        errors=error_bucket,
        valid_files=list(set(validation_status['Passed'])),
        invalid_files=list(set(validation_status['Failed'])),
        tags=tag_names
    )


if __name__ == "__main__":
    main()
