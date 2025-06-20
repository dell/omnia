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
# pylint: disable=import-error,no-name-in-module,line-too-long
import os
import subprocess
import json
import re
from ansible.module_utils.local_repo.standard_logger import setup_standard_logger


def mask_sensitive_data(cmd_string):
    """
    Masks sensitive data in command strings such as passwords, usernames, and tokens.
    """
    cmd_string = re.sub(r'(--password\s+)([^\s]+)', r'\1******', cmd_string)
    cmd_string = re.sub(r'(--username\s+)([^\s]+)', r'\1******', cmd_string)
    cmd_string = re.sub(r'(--token\s+)([^\s]+)', r'\1******', cmd_string)
    return cmd_string

def execute_command(cmd_string, logger, type_json=False):
    """
    Executes a shell command and captures the output (both stdout and stderr).

    Args:
        cmd_string (str): The shell command to execute.
        logger (logging.Logger): Logger instance for logging the process and errors.
        type_json (bool): If True, attempts to parse stdout as JSON.

    Returns:
        dict or bool: Command execution details or False on failure.
    """
    logger.info("#" * 30 + f" {execute_command.__name__} start " + "#" * 30)
    status = {}

    try:
        # Mask sensitive info before logging
        safe_cmd_string = mask_sensitive_data(cmd_string)
        logger.info(f"Executing command: {safe_cmd_string}")

        # Run the command
        cmd = subprocess.run(
            cmd_string,
            universal_newlines=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
        )

        status["returncode"] = cmd.returncode
        status["stdout"] = cmd.stdout.strip() if cmd.stdout else None
        status["stderr"] = cmd.stderr.strip() if cmd.stderr else None

        if cmd.returncode != 0:
            logger.error(f"Command failed with return code {cmd.returncode}")
            logger.error(f"Error: {status['stderr']}")
            return False

        if type_json and status["stdout"]:
            try:
                status["stdout"] = json.loads(status["stdout"])
            except json.JSONDecodeError as error:
                logger.error(f"Failed to parse JSON output: {error}")
                return False

        return status

    except Exception as error:
        logger.error(f"Error executing command: {error}")
        return False

    finally:
        logger.info("#" * 30 + f" {execute_command.__name__} end " + "#" * 30)


def write_status_to_file(status_file_path, package_name, package_type, status, logger):
    """
    Writes the status of a package to the specified status file. If the package already exists,
    its status is updated. Otherwise, the package is appended.

    Args:
        status_file_path (str): Path to the status file.
        package_name (str): Name of the package.
        package_type (str): Type of the package.
        status (str): Status of the package (e.g., "Success", "Failed").
        logger (Logger): Logger instance for logging.

    Returns:
        None
    """
    logger.info("#" * 30 + f" {write_status_to_file.__name__} start " + "#" * 30)  # Start of function

    try:
        # Check if the file exists and read its contents
        if os.path.exists(status_file_path):
            with open(status_file_path, "r") as f:
                lines = f.readlines()

            # Check if the package name already exists and replace the corresponding line
            updated = False
            with open(status_file_path, "w") as f:
                for line in lines:
                    if line.startswith(f"{package_name},"):
                        # Replace the existing line with the new status
                        f.write(f"{package_name},{package_type},{status}\n")
                        updated = True
                    else:
                        f.write(line)

                # If the package was not found, append the new line
                if not updated:
                    f.write(f"{package_name},{package_type},{status}\n")
        else:
            # If the file doesn't exist, create it and write the header and the new line
            with open(status_file_path, "w") as f:
                f.write("name,type,status\n")
                f.write(f"{package_name},{package_type},{status}\n")

        logger.info(f"Status written to {status_file_path} for {package_name}.")
    except Exception as error:
        logger.error(f"Failed to write to status file: {status_file_path}. Error: {str(error)}")
        raise RuntimeError(f"Failed to write to status file: {status_file_path}. Error: {str(error)}") from error
    finally:
        logger.info("#" * 30 + f" {write_status_to_file.__name__} end " + "#" * 30)  # End of function
