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

import os
import subprocess
import json
from jinja2 import Template
from ansible.module_utils.standard_logger import setup_standard_logger
 
# Function to execute a shell command
def execute_command(cmd_string,logger,type_json=False):
    """
    Executes a shell command and captures the output (both stdout and stderr).
 
    Args:
        cmd_string (str): The shell command to execute.
        logger (logging.Logger): Logger instance for logging the process and errors.
        type_json (bool): If set to `True`, the function will attempt to parse the command's output as JSON.
 
    Returns:
        dict or bool: Returns a dictionary with 'returncode', 'stdout', and 'stderr' on success, or `False` on failure.
    """
 
    logger.info("#" * 30 + f" {execute_command.__name__} start " + "#" * 30)  # Start of function
    status = {}
    try:
        # Log the command being executed
        logger.info(f"Executing command: {cmd_string}")
 
        # Execute the shell command and capture its output
        cmd = subprocess.run(
            cmd_string,
            universal_newlines=True,  # Ensures the output is returned as strings (not bytes)
            stdout=subprocess.PIPE,   # Capture standard output
            stderr=subprocess.PIPE,   # Capture standard error
            shell=True,               # Run the command in the shell
        )
 
        # Store command execution details
        status["returncode"] = cmd.returncode
        status["stdout"] = cmd.stdout.strip() if cmd.stdout else None
        status["stderr"] = cmd.stderr.strip() if cmd.stderr else None
 
        # Check for command failure based on return code
        if cmd.returncode != 0:
            logger.error(f"Command failed with return code {cmd.returncode}")
            logger.error(f"Error: {cmd.stderr}")
            return False
 
        # Attempt to parse JSON output if requested
        if type_json and status["stdout"]:
            try:
                status["stdout"] = json.loads(status["stdout"])
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON output: {e}")
                return False
 
        # Return the command status (stdout, stderr, and return code)
        return status
 
    # Log any exception that occurs during command execution
    except Exception as e:
        logger.error(f"Error executing command: {e}")
        return False
    finally:
        # Log function end
        logger.info("#" * 30 + f" {execute_command.__name__} end " + "#" * 30)  # End of function
 
def write_status_to_file(status_file_path, package_name, package_type, status, logger):
    """
    Writes the status of a package to the specified status file.
 
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
        with open(status_file_path, "a") as f:
            f.write(f"{package_name},{package_type},{status}\n")
        logger.info(f"Status written to {status_file_path} for {package_name}.")
    except Exception as e:
        logger.error(f"Failed to write to status file: {status_file_path}. Error: {str(e)}")
        raise RuntimeError(f"Failed to write to status file: {status_file_path}. Error: {str(e)}")
    finally:
        logger.info("#" * 30 + f" {write_status_to_file.__name__} end " + "#" * 30)  # End of function
 
