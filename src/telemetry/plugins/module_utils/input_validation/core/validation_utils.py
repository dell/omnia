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
from typing import NamedTuple
from ansible.module_utils.input_validation.messages import en_us_validation_msg
from ansible.module_utils.input_validation.core import config

def load_yaml_as_json(yaml_file, omnia_base_dir, project_name, logger, module) -> dict | None:
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

def create_error_msg(key, value, msg) -> dict:
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

def is_string_empty(value) -> bool:
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
def is_file_encrypted(file_path) -> bool:
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

class VaultError(RuntimeError):
    """Raised when an ansible-vault command fails."""


class SubprocessResult(NamedTuple):
    """Outcome of a subprocess call."""
    returncode: int
    stdout: str
    stderr: str


def run_subprocess(cmd, timeout=30) -> SubprocessResult:
    """
    Runs a subprocess command without raising and returns its outcome.

    Args:
        cmd (list): The command to run.
        timeout (int): Seconds to wait before giving up.

    Returns:
        SubprocessResult: Return code, stdout and stderr of the command.
    """
    try:
        proc = subprocess.run(
            cmd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
        return SubprocessResult(proc.returncode, proc.stdout, proc.stderr)
    except (OSError, subprocess.SubprocessError) as exc:
        return SubprocessResult(127, "", str(exc))

def read_vault_text(omnia_base_dir, project_name, vault_file, vault_password_file) -> str:
    """
    Reads an Ansible Vault encrypted file in memory using 'ansible-vault view'.
    The file on disk is never decrypted or modified.

    Args:
        omnia_base_dir (str): The base directory of the Omnia project.
        project_name (str): The name of the project.
        vault_file (str): The path to the encrypted file.
        vault_password_file (str): The path to the Ansible Vault password file.

    Returns:
        str: The decrypted file content.

    Raises:
        VaultError: If the file cannot be viewed.
    """
    password_full_path = omnia_base_dir + project_name + "/" + vault_password_file
    cmd = [
        "ansible-vault",
        "view",
        vault_file,
        "--vault-password-file",
        password_full_path,
    ]
    result = run_subprocess(cmd)
    if result.returncode != 0:
        raise VaultError(
            f"Unable to read vault file {vault_file} (rc={result.returncode}): "
            f"{result.stderr.strip()}. Please check that the associated vault key file exists."
        )
    return result.stdout

def process_encrypted_file(yaml_file, omnia_base_dir, project_name, logger, module) -> dict:
    """
    Reads an encrypted file in memory and loads its data.

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
    try:
        return yaml.safe_load(
            read_vault_text(omnia_base_dir, project_name, yaml_file, vault_password_file)
        )
    except VaultError as exc:
        logger.error(str(exc))
        module.fail_json(msg=str(exc))
    except yaml.YAMLError as exc:
        message = f"Error loading YAML in {yaml_file}: {exc}"
        logger.error(message)
        module.fail_json(msg=message)
