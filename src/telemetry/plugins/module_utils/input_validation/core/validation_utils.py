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
This module contains utility functions for input validation in the telemetry domain.
"""
import os
import yaml
import subprocess
from ansible.module_utils.input_validation.messages import en_us_validation_msg
from ansible.module_utils.input_validation.core import config

def load_yaml_as_json(yaml_file, omnia_base_dir, project_name, logger, module):
    """
    Loads a YAML file as JSON.

    Args:
        yaml_file (str): The path to the YAML file.
        omnia_base_dir (str): The base directory of the Omnia project.
        project_name (str): The name of the project.
        logger (Logger): A logger instance.
        module (AnsibleModule): An Ansible module instance.

    Returns:
        dict: The loaded YAML data as JSON.

    Raises:
        FileNotFoundError: If the YAML file is not found.
        yaml.YAMLError: If there is a syntax error in the YAML file.
    """
    try:
        if is_file_encrypted(yaml_file):
            data = process_encrypted_file(yaml_file, omnia_base_dir, project_name, logger, module)
            return data
        with open(yaml_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data
    except FileNotFoundError:
        error_message = f"File {yaml_file} not found"
        logger.error(error_message)
        module.fail_json(msg=error_message)
    except yaml.YAMLError as e:
        error_parts = []
        error_parts.append(f"Syntax error when loading YAML file '{yaml_file}'")

        if hasattr(e, 'problem_mark'):
            error_parts.append(
                f"at line {e.problem_mark.line + 1}, column {e.problem_mark.column + 1}")
            if hasattr(e, 'problem'):
                error_parts.append(f"Problem: {e.problem}")
            if hasattr(e, 'context'):
                error_parts.append(f"Context: {e.context}")
        else:
            error_parts.append(str(e))

        error_context = " | ".join(error_parts)
        logger.error(error_context)
        # Instead of raising exception immediately, return None to indicate
        # validation failure, in case there are other validations to perform
        return None

def create_error_msg(key, value, msg):
    """
    Creates an error message dictionary.

    Args:
        key (str): The key of the error.
        value (str): The value of the error.
        msg (str): The error message.

    Returns:
        dict: The error message dictionary.
    """
    return {"error_key": key, "error_value": value, "error_msg": msg}

def is_string_empty(value):
    """
    Checks if a string is empty.

    Args:
        value (str): The string to check.

    Returns:
        bool: True if the string is empty, False otherwise.
    """
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    return len(value.strip()) < 1

# Encryption-related functions (used by data_fetch.py)
def is_file_encrypted(file_path):
    """
    Checks if a file is encrypted.

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

def run_subprocess(cmd):
    """
    Runs a subprocess command and returns True if successful, False otherwise.

    Args:
        cmd (list): The command to run.

    Returns:
        bool: True if the command was successful, False otherwise.
    """
    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
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
    password_full_path = omnia_base_dir + project_name + "/" + vault_password_file
    cmd = [
        "ansible-vault",
        "encrypt",
        vault_file,
        "--vault-password-file",
        password_full_path,
    ]
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
    password_full_path = omnia_base_dir + project_name + "/" + vault_password_file
    cmd = [
        "ansible-vault",
        "decrypt",
        vault_file,
        "--vault-password-file",
        password_full_path,
    ]
    return run_subprocess(cmd)

def process_encrypted_file(yaml_file, omnia_base_dir, project_name, logger, module):
    """
    Decrypts an encrypted file, loads the data, and encrypts the file again.

    Args:
        yaml_file (str): The path to the encrypted file.
        omnia_base_dir (str): The base directory of the Omnia project.
        project_name (str): The name of the project.
        logger (Logger): A logger instance.
        module (AnsibleModule): An Ansible module instance.

    Returns:
        dict: The loaded data from the encrypted file.
    """
    vault_password_file = config.get_vault_password(yaml_file)
    decrypted_file = decrypt_file(omnia_base_dir, project_name, yaml_file, vault_password_file)
    if decrypted_file:
        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                encrypt_file(omnia_base_dir, project_name, yaml_file, vault_password_file)
                return data
        except FileNotFoundError:
            logger.error("File {%s} not found" % yaml_file)
            module.fail_json(msg="File {%s} not found" % (yaml_file))
        except yaml.YAMLError as e:
            logger.error(f"Error loading YAML: {e}")
            module.fail_json(f"Error loading YAML: {e}")
    else:
        unable_to_decrypt_fail_msg = (
            f"Error occured when attempting to decrypt file. "
            f"Please check that the assoicated vault file exists for {yaml_file}"
        )
        logger.error(unable_to_decrypt_fail_msg)
        module.fail_json(unable_to_decrypt_fail_msg)
