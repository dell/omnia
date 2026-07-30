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
"""
File utilities for input validation.

This module provides functions for:
- File and directory existence verification
- Reading and parsing JSON/YAML files
- Line number extraction for error reporting
- Recursive file discovery
"""
import glob
import os
import json
import yaml
import subprocess

from ansible.module_utils.input_validation.core.config import get_vault_password

# =============================================================================
# FILE/DIRECTORY VERIFICATION
# =============================================================================


def file_exists(file_path, module, logger):
    """
    Verify if a file exists at the given path.

    Args:
        file_path (str): The path of the file.
        module: Ansible module instance.
        logger: Logger instance.

    Returns:
        bool: True if the file exists, False otherwise.
    """
    if os.path.exists(file_path) and os.path.isfile(file_path):
        logger.info(f"The file {file_path} exists")
        return True
    message = f"The file {file_path} does not exist"
    logger.error(message)
    module.fail_json(msg=message)
    return False


def directory_exists(directory_path, module, logger):
    """
    Verify if a directory exists at the given path.

    Args:
        directory_path (str): The path of the directory to check.
        module: Ansible module instance.
        logger: Logger instance.

    Returns:
        bool: True if the directory exists, False otherwise.
    """
    if os.path.exists(directory_path) and os.path.isdir(directory_path):
        logger.info(f"The directory {directory_path} exists.")
        return True
    message = f"The directory {directory_path} does not exist."
    logger.error(message)
    module.fail_json(msg=message)
    return False


def verify_path(file_path):
    """
    Verifies if a file exists at the given path.

    Args:
        file_path (str): The path to the file.

    Returns:
        bool: True if the file exists, False otherwise.
    """
    if not os.path.exists(file_path):
        return False
    return os.path.isfile(file_path)


# =============================================================================
# FILE DISCOVERY
# =============================================================================

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


# =============================================================================
# LINE NUMBER EXTRACTION
# =============================================================================

def json_line_number(file_path, json_path, module):
    """
    Get the line number of a specific json_path in a file.

    Args:
        file_path (str): The path to the file.
        json_path (str): The json_path to search for.
        module: Ansible module instance.

    Returns:
        tuple: A tuple containing the line number and a boolean indicating
            if the line number is valid. If the line number is not found, returns None.
    """
    is_line_num = True
    if '.' in json_path:
        json_path = json_path.split('.')[0] + "\":"
        is_line_num = False
    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()
        if not lines:
            message = f"Unable to access and read file: {file_path}"
            module.fail_json(msg=message)
        for lineno, line in enumerate(lines, start=1):
            if json_path in line:
                return lineno, is_line_num
    return None


def yml_line_number(file_path, yml_path, omnia_base_dir, project_name):
    """
    Get the line number of a specific YAML path in a file.

    Args:
        file_path (str): The path to the file.
        yml_path (str): The YAML path to search for.
        omnia_base_dir (str): Base directory for Omnia.
        project_name (str): Project name.

    Returns:
        tuple: A tuple containing the line number and a boolean
            indicating if the line number is valid.
    """
    is_line_num = True
    if "." in yml_path:
        yml_path = yml_path.split(".")[0]
        is_line_num = False

    if is_file_encrypted(file_path):
        vault_password_file = get_vault_password(file_path)
        decrypt_file(omnia_base_dir, project_name, file_path, vault_password_file)
        with open(file_path, "r", encoding="utf-8") as file:
            for lineno, line in enumerate(file, start=1):
                if line and not line.startswith("#") and yml_path in line:
                    encrypt_file(omnia_base_dir, project_name, file_path, vault_password_file)
                    return lineno, is_line_num
        encrypt_file(omnia_base_dir, project_name, file_path, vault_password_file)
        return None

    with open(file_path, "r", encoding="utf-8") as file:
        for lineno, line in enumerate(file, start=1):
            if line and not line.startswith("#") and yml_path in line:
                return lineno, is_line_num
    return None


# =============================================================================
# FILE READING
# =============================================================================

def input_data(input_file_path, omnia_base_dir, project_name, logger, module):
    """
    Loads input data from a file based on its extension.

    Args:
        input_file_path (str): The path to the input file.
        omnia_base_dir (str): Base directory for Omnia.
        project_name (str): Project name.
        logger: Logger instance.
        module: Ansible module instance.

    Returns:
        tuple: A tuple containing the loaded data and the file extension.

    Raises:
        ValueError: If the file extension is unsupported.
    """
    _, extension = os.path.splitext(input_file_path)

    if "json" in extension:
        try:
            with open(input_file_path, "r", encoding="utf-8") as file_obj:
                return json.load(file_obj), extension
        except json.JSONDecodeError as e:
            error_msg = (
                f"Failed to parse JSON file '{input_file_path}':\n"
                f"Error: {e.msg}\n"
                f"Line {e.lineno}, Column {e.colno}\n"
                f"Please check the JSON syntax in the file."
            )
            logger.error(error_msg)
            return None, extension
        except FileNotFoundError:
            logger.error(f"File not found: {input_file_path}")
            return None, extension
        except (IOError, OSError, PermissionError) as exc:
            logger.error(f"Error reading {input_file_path}: {exc}")
            return None, extension
        except Exception as exc:
            logger.error(f"Unexpected error reading {input_file_path}: {exc}")
            return None, extension

    if "yml" in extension or "yaml" in extension:
        return (
            load_yaml_as_json(input_file_path, omnia_base_dir, project_name, logger, module),
            extension,
        )

    raise ValueError(f"Unsupported file extension: {extension}")


def load_yaml_as_json(yaml_file, omnia_base_dir, project_name, logger, module):
    """
    Loads a YAML file as JSON.

    Args:
        yaml_file (str): The path to the YAML file.
        omnia_base_dir (str): The base directory of the Omnia project.
        project_name (str): The name of the project.
        logger: Logger instance.
        module: Ansible module instance.

    Returns:
        dict: The loaded YAML data as JSON.
    """
    try:
        if is_file_encrypted(yaml_file):
            return process_encrypted_file(yaml_file, omnia_base_dir, project_name, logger, module)
        with open(yaml_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"File {yaml_file} not found")
        module.fail_json(msg=f"File {yaml_file} not found")
    except yaml.YAMLError as e:
        error_parts = [f"Syntax error when loading YAML file '{yaml_file}'"]
        if hasattr(e, 'problem_mark'):
            error_parts.append(
                f"at line {e.problem_mark.line + 1}, column {e.problem_mark.column + 1}")
            if hasattr(e, 'problem'):
                error_parts.append(f"Problem: {e.problem}")
            if hasattr(e, 'context'):
                error_parts.append(f"Context: {e.context}")
        else:
            error_parts.append(str(e))
        logger.error(" | ".join(error_parts))
        return None


def load_json(file_path):
    """
    Load JSON data from a file.

    Args:
        file_path (str): The path to the JSON file.

    Returns:
        dict: The loaded JSON data.

    Raises:
        FileNotFoundError: If the file is not found.
        ValueError: If the JSON parsing fails.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Error: File '{file_path}' not found.") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Error: Failed to parse JSON in file '{file_path}'.") from exc


# =============================================================================
# ENCRYPTION UTILITIES
# =============================================================================

def is_file_encrypted(file_path):
    """
    Checks if a file is encrypted with Ansible Vault.

    Args:
        file_path (str): The path to the file.

    Returns:
        bool: True if the file is encrypted, False otherwise.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            first_line = file.readline().strip()
            return first_line.startswith('$ANSIBLE_VAULT')
    except (IOError, OSError):
        return False


def process_encrypted_file(yaml_file, omnia_base_dir, project_name, logger, module):
    """
    Decrypts an encrypted file, loads the data, and encrypts the file again.

    Args:
        yaml_file (str): The path to the encrypted file.
        omnia_base_dir (str): The base directory of the Omnia project.
        project_name (str): The name of the project.
        logger: Logger instance.
        module: Ansible module instance.

    Returns:
        dict: The loaded data from the encrypted file.
    """
    vault_password_file = get_vault_password(yaml_file)
    decrypted_file = decrypt_file(omnia_base_dir, project_name, yaml_file, vault_password_file)

    if decrypted_file:
        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                encrypt_file(omnia_base_dir, project_name, yaml_file, vault_password_file)
                return data
        except FileNotFoundError:
            logger.error(f"File {yaml_file} not found")
            module.fail_json(msg=f"File {yaml_file} not found")
        except yaml.YAMLError as e:
            logger.error(f"Error loading YAML: {e}")
            module.fail_json(f"Error loading YAML: {e}")
    else:
        msg = f"Error occurred when attempting to decrypt file. Please check vault file for {yaml_file}"
        logger.error(msg)
        module.fail_json(msg)


def run_subprocess(cmd):
    """
    Runs a subprocess command and returns True if successful.

    Args:
        cmd (list): The command to run.

    Returns:
        bool: True if the command was successful, False otherwise.
    """
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return True
    except subprocess.CalledProcessError:
        return False


def encrypt_file(omnia_base_dir, project_name, vault_file, vault_password_file):
    """
    Encrypts a file using Ansible Vault.

    Args:
        omnia_base_dir (str): The base directory of the Omnia project.
        project_name (str): The name of the project.
        vault_file (str): The path to the file to encrypt.
        vault_password_file (str): The path to the Ansible Vault password file.

    Returns:
        bool: True if the encryption was successful, False otherwise.
    """
    password_full_path = os.path.join(os.path.dirname(vault_file), vault_password_file)
    cmd = ["ansible-vault", "encrypt", vault_file, "--vault-password-file", password_full_path]
    return run_subprocess(cmd)


def decrypt_file(omnia_base_dir, project_name, vault_file, vault_password_file):
    """
    Decrypts a file using Ansible Vault.

    Args:
        omnia_base_dir (str): The base directory of the Omnia project.
        project_name (str): The name of the project.
        vault_file (str): The path to the file to decrypt.
        vault_password_file (str): The path to the Ansible Vault password file.

    Returns:
        bool: True if the decryption was successful, False otherwise.
    """
    password_full_path = os.path.join(os.path.dirname(vault_file), vault_password_file)
    cmd = ["ansible-vault", "decrypt", vault_file, "--vault-password-file", password_full_path]
    return run_subprocess(cmd)
