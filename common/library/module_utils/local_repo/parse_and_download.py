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
# pylint: disable=import-error,no-name-in-module
"""
Utility functions for parsing and downloading artifacts.

This module provides common functions for command execution, status file management,
and repository operations used across the local repo management system.
"""

import os
import subprocess
import json
import re
from multiprocessing import Lock
from ansible.module_utils.local_repo.config import ARCH_SUFFIXES, STATUS_CSV_HEADER


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

        if type_json:
            if not status["stdout"]:
                logger.error("Command succeeded but returned empty output when JSON was expected")
                return False
            try:
                status["stdout"] = json.loads(status["stdout"])
            except json.JSONDecodeError as error:
                logger.error(f"Failed to parse JSON output: {error}")
                logger.error(f"Raw output was: {status['stdout']}")
                return False

        logger.info(f"Command succeeded: {safe_cmd_string}")
        return status
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {safe_cmd_string} - {e}")
        return False
    except subprocess.TimeoutExpired as e:
        logger.error(f"Command timed out: {safe_cmd_string} - {e}")
        return False
    except OSError as e:
        logger.error(f"OS error during command: {safe_cmd_string} - {e}")
        return False

    finally:
        logger.info("#" * 30 + f" {execute_command.__name__} end " + "#" * 30)

def get_arch_from_status_path(status_file_path):
    """Extract architecture from status file path.
    
    Args:
        status_file_path: Path like '/opt/omnia/log/local_repo/x86_64/software_name/status.csv'
        
    Returns:
        str: Architecture ('x86_64' or 'aarch64') or None if not found
    """
    for arch in ARCH_SUFFIXES:
        if f"/{arch}/" in status_file_path:
            return arch
    return None

def _prefix_repo_name_with_arch(repo_name: str, status_file_path: str, logger) -> str:
    """Add architecture prefix to repo_name if not already present.
    
    Args:
        repo_name: Repository name to prefix
        status_file_path: Path to extract architecture from
        logger: Logger instance
        
    Returns:
        str: Repository name with architecture prefix
    """
    if not repo_name:
        return repo_name
        
    arch = get_arch_from_status_path(status_file_path)
    if arch and not any(repo_name.startswith(f"{prefix}_") for prefix in ARCH_SUFFIXES):
        prefixed_name = f"{arch}_{repo_name}"
        logger.info(f"Auto-prefixed repo_name with architecture: {prefixed_name}")
        return prefixed_name
    return repo_name


def _update_existing_line(line: str, package_name: str, package_type: str, status: str, repo_name: str, status_file_path: str) -> str:
    """Update an existing line in status file.
    
    Args:
        line: Existing line content
        package_name: Package name to match
        package_type: Package type
        status: New status
        repo_name: Repository name
        status_file_path: Path for architecture extraction
        
    Returns:
        str: Updated line content
    """
    parts = line.strip().split(',')
    if len(parts) >= 4:
        final_repo_name = _prefix_repo_name_with_arch(repo_name, status_file_path, None)
        parts[2] = final_repo_name if final_repo_name else ''
        parts[3] = status
        return ','.join(parts) + '\n'
    
    # Handle short lines
    final_repo_name = _prefix_repo_name_with_arch(repo_name, status_file_path, None)
    return f"{package_name},{package_type},{final_repo_name if final_repo_name else ''},{status}\n"


def write_status_to_file(status_file_path, package_name, package_type, status, logger, file_lock: Lock, repo_name=None):
    """
    Writes or updates the status of a package in the status file.
    
    Args:
        status_file_path: Path to the status file
        package_name: Name of the package
        package_type: Type of the package (rpm, image, etc.)
        status: Status (Success, Failed, etc.)
        logger: Logger instance
        file_lock: Lock for thread safety
        repo_name: Optional repository name (for RPMs)
    """
    logger.info("#" * 30 + f" {write_status_to_file.__name__} start " + "#" * 30)

    # Auto-prefix repo_name with architecture if needed
    repo_name = _prefix_repo_name_with_arch(repo_name, status_file_path, logger)

    try:
        with file_lock:  # Ensure only one process can write at a time
            if os.path.exists(status_file_path):
                _update_existing_file(status_file_path, package_name, package_type, status, repo_name)
            else:
                _create_new_file(status_file_path, package_name, package_type, status, repo_name)

            logger.info(f"Status written to {status_file_path} for {package_name}.")
    except OSError as e:
        logger.error(f"Failed to write to status file: {status_file_path}. Error: {str(e)}")
        raise RuntimeError(
            f"Failed to write to status file: {status_file_path}. Error: {str(e)}"
        ) from e
    finally:
        logger.info("#" * 30 + f" {write_status_to_file.__name__} end " + "#" * 30)


def _update_existing_file(status_file_path, package_name, package_type, status, repo_name):
    """Update existing status file with new package status."""
    with open(status_file_path, "r", encoding='utf-8') as f:
        lines = f.readlines()

    updated = False
    with open(status_file_path, "w", encoding='utf-8') as f:
        # Write header
        if lines:
            f.write(lines[0])

        # Write data lines
        for line in lines[1:]:  # Skip header
            if line.startswith(f"{package_name},"):
                updated_line = _update_existing_line(
                    line, package_name, package_type, status, repo_name, status_file_path
                )
                f.write(updated_line)
                updated = True
            else:
                f.write(line)

        if not updated:
            final_repo_name = _prefix_repo_name_with_arch(repo_name, status_file_path, None)
            f.write(f"{package_name},{package_type},{final_repo_name if final_repo_name else ''},{status}\n")


def _create_new_file(status_file_path, package_name, package_type, status, repo_name):
    """Create new status file with package status."""
    with open(status_file_path, "w", encoding='utf-8') as f:
        f.write(STATUS_CSV_HEADER)
        final_repo_name = _prefix_repo_name_with_arch(repo_name, status_file_path, None)
        f.write(f"{package_name},{package_type},{final_repo_name if final_repo_name else ''},{status}\n")
