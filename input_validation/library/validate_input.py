# Copyright 2024 Dell Inc. or its subsidiaries. All Rights Reserved.
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
import json
import yaml
import glob
import os
import logging
import jsonschema
import subprocess
from ansible.module_utils.basic import AnsibleModule

import sys
sys.path.append("module_utils/common")

import logical_validation
import validation_utils
import config

def createLogger(project_name, tag_name=None):
    if tag_name:
        log_filename = f"{tag_name}_validation_omnia_{project_name}.log"
    else:
        log_filename = f"validation_omnia_{project_name}.log"
    logging.basicConfig(
        filename=log_filename,
        format="%(asctime)s %(message)s",
        filemode="w"
    )
    logger = logging.getLogger(tag_name if tag_name else project_name)
    logger.setLevel(logging.DEBUG)
    return logger

def main():
    module_args = dict(
        omnia_base_dir=dict(type="str", required=True),
        project_name=dict(type="str", required=True),
        tag_names=dict(type="str", required=True),
        files=dict(type="list", elements="str", required=False)
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    omnia_base_dir = module.params["omnia_base_dir"]
    project_name = module.params["project_name"]
    tag_names = eval(module.params["tag_names"])
    single_files = module.params["files"]
    
    schema_base_file_path = "./module_utils/schema/"
    directory_path = os.path.join(omnia_base_dir, project_name)
    
    input_file_inventory = config.input_file_inventory
    passwords_set = config.passwords_set
    extensions = config.extensions

    json_files_dic = {}
    yml_files_dic = {}
    schema_files_dic = {}
    validation_status = {}
    vstatus = []
    
    logger = createLogger(project_name)

### Functions related to files, pathing, and verifying if they exist ###
# Function to get all files of a specific type recursively from a directory
    def get_files_recursively(directory, file_type):
        file_list = []
        for file_path in glob.iglob(f"{directory}/**/*" + file_type, recursive=True):
            if os.path.isfile(file_path):
                file_list.append(os.path.abspath(file_path))
        return file_list
# Function to verify if a file exists at the given path
    def verify_file_exists(file_path):
        if os.path.exists(file_path) and os.path.isfile(file_path):
            message = "The file %s exists" % file_path
            logger.info(message)
            return True
        else:
            message = "The file %s does not exist" % file_path
            logger.error(message)
            module.fail_json(msg=message)
            return False
# Function to get the file name from a given file path
    def get_file_name_from_path(file_path):
        return os.path.basename(file_path)
# Function to verify if a directory exists at the given path
    def verify_directory_exists(directory_path):
        if os.path.exists(directory_path) and os.path.isdir(directory_path):
            message = "The directory %s exists." % directory_path
            logger.info(message)
            return True
        else:
            message = "The directory %s does not exist." % directory_path
            logger.error(message)
            module.fail_json(msg=message)
            return False

# Below are the functions that will get the line number
# Function to get the line number of a specific json_path (ex: (switch_details.ip) in a file
    def get_json_line_number(file_path, json_path):
        is_line_num = True
        if '.' in json_path:
            json_path = json_path.split('.')[0] + "\":"
            is_line_num = False
        with open(file_path, "r") as file:
            lines = file.readlines()
            if not (lines):
                message = f"Unable to access and read file: {file_path}"
                module.fail_json(msg=message)
            # Iterate through the lines to find the JSON path
            for lineno, line in enumerate(lines, start=1):
                if json_path in line:
                    return lineno, is_line_num
        return None
# Function to get the line number of a specific yaml_path (switch_details.ip) in a file
    def get_yml_line_number(file_path, yml_path):
        is_line_num = True
        # Check if the YAML path contains a dot and adjust the path accordingly
        if '.' in yml_path:
            yml_path = yml_path.split('.')[0]
            is_line_num = False
        # If the file is encrypted, decrypt and read data, then reencrypt
        if validation_utils.is_file_encrypted(file_path):
            vault_password_file = config.get_vault_password(file_path)
            validation_utils.decrypt_file(omnia_base_dir, project_name, file_path, vault_password_file)
            with open(file_path, "r") as file:
                for lineno, line in enumerate(file, start=1):
                    if line and not line.startswith('#') and yml_path in line:
                        validation_utils.encrypt_file(omnia_base_dir, project_name, file_path, vault_password_file)
                        return lineno, is_line_num
            validation_utils.encrypt_file(omnia_base_dir, project_name, file_path, vault_password_file)
            return None
        # else open file and read its line
        else:
            with open(file_path, "r") as file:
                for lineno, line in enumerate(file, start=1):
                    if line and not line.startswith('#') and yml_path in line:
                        return lineno, is_line_num
            return None
    
    # Function to load input data from a file based on its extension
    def get_input_data(input_file_path):
        _, extension = os.path.splitext(input_file_path)
        if "json" in extension:
            return json.load(open(input_file_path, "r")), extension
        elif "yml" in extension or "yaml" in extension:
            return validation_utils.load_yaml_as_json(input_file_path, omnia_base_dir, project_name, logger, module), extension
        else:
            message = f"Unsupported file extension: {extension}"
            raise ValueError(message)
        
    # Main L1 Validation code. Get the JSON schema and input file to validate
    def validate_schema(input_file_path, schema_file_path):
        try:
            input_data, extension = get_input_data(input_file_path)
            schema = json.load(open(schema_file_path, "r"))

            message = f"{'#' * 10} Validation Initiated for {input_file_path} {'#' * 10}"
            logger.debug(message)
            
            # Validate the input file with the schema and output the errors
            validator = jsonschema.Draft7Validator(schema)
            errors = sorted(validator.iter_errors(input_data), key=lambda e: e.path)

            # if errors exist, then print an error with the line number
            if errors:    
                for error in errors:
                    error_path = ".".join(map(str, error.path))
                    error_msg = f"Validation Error at {error_path}: {error.message}"

                    # For passwords, mask the value so that no password values are logged
                    if (error.path[-1] in passwords_set):
                        parts = error.message.split(' ', 1)
                        if parts:
                            parts[0] = f"'{'*' * (len(parts[0]) - 2)}'"
                        error_msg = f"Validation Error at {error_path}: {' '.join(parts)}"
                    # For all other fields, just log the value
                    logger.error(error_msg)

                    # get the line number and log it
                    line_number, is_line_num = None, False
                    if "json" in extension:
                        line_number, is_line_num = get_json_line_number(input_file_path, error_path)
                    elif "yml" in extension:
                        line_number, is_line_num = get_yml_line_number(input_file_path, error_path)
                        logger.info(line_number, is_line_num)
                    if line_number:
                        message = f"Error occurs on line {line_number}" if is_line_num else f"Error occurs on object or list entry on line {line_number}"
                        logger.error(message)
                message = f"{'#' * 10} Schema Validation failed for {input_file_path} {'#' * 10}"
                logger.error(message)
                return False
            else:
                message = f"{'#' * 10} Schema Validation successful for {input_file_path} {'#' * 10}"
                logger.info(message)
                return True
        except jsonschema.exceptions.SchemaError as se:
            message = f"Internal schema validation error: {se.message}"
            logger.error(message)
        except ValueError as ve:
            message = f"Value error: {ve}"
            logger.error(message)
        except Exception as e:
            message = f"An unexpected error occurred: {e}"
            logger.error(message)
            
    # Code to run the L2 validation validate_input_logic function.
    def validate_logic(input_file_path, logger, module, omnia_base_dir, project_name):
        try:
            input_data, extension = get_input_data(input_file_path)
            
            # errors = [{error_msg: custom message, error_key: ex-node_name (to find line number), error_value: ex-6,"node" (to help find line #)}]
            errors = logical_validation.validate_input_logic(input_file_path, input_data, logger, module, omnia_base_dir, project_name)

            # Print errors, if the error value is None then send a separate message.
            # This is for values where it did not have a single key as the error
            if errors:       
                for error in errors:
                    error_key = error['error_key']
                    error_value = error['error_value']
                    error_msg = error['error_msg']

                    # Log the error message based on the error value
                    if error_value is None:
                        message = f"Validation Error at {error_key} {error_msg}"
                        logger.error(message)
                    elif isinstance(error_value, str):
                        message = f"Validation Error at {error_key}: '{error_value}' {error_msg}"
                        logger.error(message)
                    else:
                        message = f"Validation Error at {error_key}: {error_value} {error_msg}"
                        logger.error(message)

                    # log the line number based off of the input config file extension
                    if "json" in extension:
                        line_number, is_line_num = get_json_line_number(input_file_path, error_key)
                        if line_number:
                            message = f"Error occurs on line {line_number}" if is_line_num else f"Error occurs on object or list entry on line {line_number}"
                            logger.error(message)
                    if "yml" in extension:
                        if error_value is None:
                            continue
                        line_number, is_line_num = get_yml_line_number(input_file_path, error_key)
                        if line_number:
                            message = f"Error occurs on line {line_number}" if is_line_num else f"Error occurs on object or list entry on line {line_number}"
                            logger.error(message)

                message = f"{'#' * 10} Logic Validation failed for {input_file_path} {'#' * 10}"
                logger.error(message)
                return False
            else:
                message = f"{'#' * 10} Logic Validation successful for {input_file_path} {'#' * 10}"
                logger.info(message)
                return True
        except ValueError as ve:
            message = f"Value error: {ve}"
            logger.error(message)
        except Exception as e:
            message = f"An unexpected error occurred: {e}"
            logger.error(message)
            
    # Start validation execution        
    message = f"{'#' * 30} START EXECUTION {'#' * 30}"
    logger.info(message)
    
    # Check if the specified directory exists
    if not verify_directory_exists(directory_path):
        error_message = f"The directory {directory_path} does not exist."
        logger.info(error_message)
        raise FileNotFoundError(error_message)
    
    json_files = get_files_recursively(omnia_base_dir + "/" + project_name, extensions['json'])
    yml_files = get_files_recursively(omnia_base_dir + "/" + project_name, extensions['yml'])
    schema_files = get_files_recursively(schema_base_file_path, extensions['json'])

    for file_path in json_files:
        json_files_dic.update({get_file_name_from_path(file_path): file_path})
    for file_path in yml_files:
        yml_files_dic.update({get_file_name_from_path(file_path): file_path})
    for file_path in schema_files:
        schema_files_dic.update({get_file_name_from_path(file_path): file_path})

    if not json_files and not yml_files:
        error_message = f"yml and json files not found in directory: {directory_path}"
        logger.error(error_message)
        module.fail_json(msg=error_message)
        raise FileNotFoundError(error_message)

    # For each file from the tag names, run schema validation (L1) and logic validation (L2)
    s = {project_name: {"status": [], "tag": tag_names}}

    if (len(single_files) > 0):
        for name in single_files:
            if not (name):
                continue
            validation_status.update(s)
            fname = os.path.splitext(name)[0]
            schema_file_path = schema_base_file_path + fname + extensions['json']
            input_file_path = None
            
            if not verify_file_exists(schema_file_path):
                error_message = f"The file schema: {fname}.json does not exist in directory: {schema_base_file_path}."
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
            schema_status = validate_schema(input_file_path, schema_file_path)
            # Append the validation status for the input file
            validation_status[project_name]["status"].append({input_file_path: "Passed" if schema_status else "Failed"})
            if len(tag_names) == 0:
                validation_status[project_name]["tag"] = ['none']
                
            vstatus.append(schema_status)
    # Run L1 and L2 validation if user included a tag and extra var files. Or user only had tags and no extra var files.         
    if (len(tag_names) > 0 and "all" not in tag_names and len(single_files) > 0) or (len(tag_names) > 0 and len(single_files) == 0):
        for tag_name in tag_names:
            for name in input_file_inventory[tag_name]:
                validation_status.update(s)
                fname, _ = os.path.splitext(name)
                schema_file_path = schema_base_file_path + fname + extensions['json']
                input_file_path = None

                if not verify_file_exists(schema_file_path):
                    error_message = f"The file schema: {fname}.json does not exist in directory: {schema_base_file_path}."
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
                schema_status = validate_schema(input_file_path, schema_file_path)
                # Validate the logic of the input file (L2)
                individual_logger = createLogger(project_name, tag_name)
                logic_status = validate_logic(input_file_path, individual_logger, module, omnia_base_dir, project_name)
                
                # Append the validation status for the input file
                validation_status[project_name]["status"].append({input_file_path: "Passed" if (schema_status and logic_status) else "Failed"})
                
                # vstatus contains boolean values. If False exists, that means validation failed and the module will result in failure
                vstatus.append(schema_status)
                vstatus.append(logic_status)
    
    if not validation_status:
        message = "No validation has been performed. Please provide tags or include individual file names."
        module.fail_json(msg=message)
    validation_status[project_name]["status"].sort(key=lambda x: list(x.values())[0])
    
    message = f"{'#' * 30} END EXECUTION {'#' * 30}"
    logger.error(message)
    
    # Ansible success/failure message
    if False in vstatus:
        status = validation_status['input']['status']
        tag = validation_status['input']['tag']
        failed_files = [file for item in status for file, result in item.items() if result == 'Failed']
        passed_files = [file.split("/")[-1] for item in status for file, result in item.items() if result == 'Passed']
        message = (
            "Input validation failed for: %s input configuration(s). Validation passed for %s. "
            "Tag(s) run: %s. Look at the logs for more details: filename=validation_omnia_%s.log"
            % (failed_files, passed_files, tag, project_name)
        )
        module.fail_json(msg=message)
    else: 
        message = (
            "Input validation completed for project: %s input configs. Look at the logs for more details: filename=validation_omnia_%s.log"
            % (validation_status, project_name)
            + "s"
        )
        module.exit_json(msg=message)


if __name__ == "__main__":
    main()
