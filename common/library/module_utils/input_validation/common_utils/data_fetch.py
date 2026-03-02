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
"""
This module is used to fetch data from files
"""
#!/usr/bin/python

import glob
import os
import json
from ansible.module_utils.input_validation.common_utils import validation_utils
from ansible.module_utils.input_validation.common_utils import config


# Function to get all files of a specific type recursively from a directory
def files_recursively(directory, file_type):
    """
    Returns a list of absolute file paths of all files
        of a specific type recursively from a directory.

    Args:
        directory (str): The base directory to search for files.
        file_type (str): The file type to search for.

    Returns:
        list: A list of absolute file paths.
    """
    file_list = []
    for file_path in glob.iglob(f"{directory}/**/*" + file_type, recursive=True):
        if os.path.isfile(file_path):
            file_list.append(os.path.abspath(file_path))
    return file_list


def file_name_from_path(file_path):
    """
    Get the file name from a given file path.
    Args:
        file_path (str): The path of the file.
    Returns:
        str: The file name.
    """
    return os.path.basename(file_path)


def json_line_number(file_path, json_path, module):
    """
    Get the line number of a specific json_path in a file.

    Args:
        file_path (str): The path to the file.
        json_path (str): The json_path to search for.

    Returns:
        tuple: A tuple containing the line number and a boolean indicating
            if the line number is valid. If the line number is not found, returns None.
    """
    is_line_num = True
    if '.' in json_path:
        json_path = json_path.split('.')[0] + "\":"
        is_line_num = False
    with open(file_path, "r") as file:
        lines = file.readlines()
        if not lines:
            message = f"Unable to access and read file: {file_path}"
            module.fail_json(msg=message)
        # Iterate through the lines to find the JSON path
        for lineno, line in enumerate(lines, start=1):
            if json_path in line:
                return lineno, is_line_num
    return None


# Function to get the line number of a specific yaml_path in a file
def yml_line_number(file_path, yml_path, omnia_base_dir, project_name):
    """
    Get the line number of a specific YAML path in a file.

    Args:
        file_path (str): The path to the file.
        yml_path (str): The YAML path to search for.

    Returns:
        tuple: A tuple containing the line number and a boolean
            indicating if the line number is valid.
                Returns None if the line number is not found.
    """
    is_line_num = True
    # Check if the YAML path contains a dot and adjust the path accordingly
    if "." in yml_path:
        yml_path = yml_path.split(".")[0]
        is_line_num = False
    # If the file is encrypted, decrypt and read data, then reencrypt
    if validation_utils.is_file_encrypted(file_path):
        vault_password_file = config.get_vault_password(file_path)
        validation_utils.decrypt_file(omnia_base_dir, project_name, file_path, vault_password_file)
        with open(file_path, "r", encoding="utf-8") as file:
            for lineno, line in enumerate(file, start=1):
                if line and not line.startswith("#") and yml_path in line:
                    validation_utils.encrypt_file(
                        omnia_base_dir, project_name, file_path, vault_password_file
                    )
                    return lineno, is_line_num
        validation_utils.encrypt_file(omnia_base_dir, project_name, file_path, vault_password_file)
        return None
    # else open file and read its line
    with open(file_path, "r", encoding="utf-8") as file:
        for lineno, line in enumerate(file, start=1):
            if line and not line.startswith("#") and yml_path in line:
                return lineno, is_line_num
    return None


# Function to load input data from a file based on its extension
def input_data(input_file_path, omnia_base_dir, project_name, logger, module):
    """
    Loads input data from a file based on its extension.

    Args:
        input_file_path (str): The path to the input file.

    Returns:
        Tuple[Any, str]: A tuple containing the loaded data and the file extension.

    Raises:
        ValueError: If the file extension is unsupported.
    """
    _, extension = os.path.splitext(input_file_path)
    if "json" in extension:
        return json.load(open(input_file_path, "r")), extension
    if "yml" in extension or "yaml" in extension:
        return (
            validation_utils.load_yaml_as_json(
                input_file_path, omnia_base_dir, project_name, logger, module
            ),
            extension,
        )
    message = f"Unsupported file extension: {extension}"
    raise ValueError(message)
