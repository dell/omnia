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
# pylint: disable=import-error,no-name-in-module,too-many-arguments
# pylint: disable=too-many-positional-arguments,too-many-locals
"""
Utility functions for parsing and downloading artifacts.

This module provides common functions for command execution, status file management,
and repository operations used across the repo manager system.
"""

import os
import subprocess
import json
import re
import shlex
from multiprocessing import Lock
from ansible.module_utils.repo_manager.config import ARCH_SUFFIXES, STATUS_CSV_HEADER
from ansible.module_utils.repo_manager.mirror_status import (
    load_mirror_index,
    save_mirror_index,
    update_mirror_index_entry
)


def mask_sensitive_data(cmd_string):
    """
    Masks sensitive data in command strings such as passwords, usernames, and tokens.
    """
    cmd_string = re.sub(r'(--password\s+)([^\s]+)', r'\1******', cmd_string)
    cmd_string = re.sub(r'(--username\s+)([^\s]+)', r'\1******', cmd_string)
    cmd_string = re.sub(r'(--token\s+)([^\s]+)', r'\1******', cmd_string)
    return cmd_string


def execute_command(cmd_string, logger, type_json=False):  # pylint: disable=too-many-return-statements
    """
    Executes a command and captures the output (both stdout and stderr).

    Uses shell=False and shlex.split() for plain commands. Shell=True is only
    used when the command string contains shell metacharacters (e.g. pipes).

    Args:
        cmd_string (str): The command to execute.
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

        # Use shell=True only when the command contains shell metacharacters.
        # Otherwise parse the string into an argument list and run shell=False.
        shell_metacharacters = re.compile(r'[|&;<>$`\(\)\[\]\*\?\{\}]')
        use_shell = bool(shell_metacharacters.search(cmd_string))
        cmd_args = cmd_string if use_shell else shlex.split(cmd_string)

        # Run the command
        # nosec B602 - shell=True is required for commands with shell metacharacters
        cmd = subprocess.run(
            cmd_args,
            universal_newlines=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=use_shell,  # nosec B602
            check=False
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
                logger.error(
                    "Command succeeded but returned empty output when JSON was expected")
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
        status_file_path: Path like 'log/repo_manager/x86_64/software_name/status.csv'

    Returns:
        str: Architecture ('x86_64' or 'aarch64') or None if not found
    """
    for arch in ARCH_SUFFIXES:
        if f"/{arch}/" in status_file_path:
            return arch
    return None


def get_os_info_from_status_path(status_file_path):
    """Extract OS type and version from status file path.

    The expected path pattern is:
        .../<os_type>/<os_version>/<arch>/<software>/status.csv
    e.g., log/repo_manager/rhel/10.0/x86_64/software_name/status.csv

    Args:
        status_file_path: Path to status file

    Returns:
        tuple: (os_type, os_version) or (None, None) if not found
    """
    for arch in ARCH_SUFFIXES:
        marker = f"/{arch}/"
        idx = status_file_path.find(marker)
        if idx > 0:
            # Everything before /<arch>/ contains .../<os_type>/<os_version>
            prefix = status_file_path[:idx]
            parts = prefix.rstrip("/").rsplit("/", 2)
            if len(parts) >= 3:
                return parts[-2], parts[-1]
    return None, None


def _prefix_repo_name_with_arch(repo_name: str, status_file_path: str, logger) -> str:
    """Add architecture and OS prefix to repo_name if not already present.

    Builds prefix: <arch>_<os_type>_<os_version>_
    e.g., x86_64_rhel_10.0_

    Args:
        repo_name: Repository name to prefix
        status_file_path: Path to extract architecture and OS info from
        logger: Logger instance

    Returns:
        str: Repository name with architecture and OS prefix
    """
    if not repo_name:
        return repo_name

    arch = get_arch_from_status_path(status_file_path)
    if arch and not any(repo_name.startswith(f"{prefix}_") for prefix in ARCH_SUFFIXES):
        os_type, os_version = get_os_info_from_status_path(status_file_path)
        if os_type and os_version:
            # Lazy import to avoid circular dependency (software_utils imports from this module)
            # pylint: disable=import-outside-toplevel
            from ansible.module_utils.repo_manager.software_utils import build_repo_name_prefix
            prefixed_name = build_repo_name_prefix(arch, os_type, os_version) + repo_name
        else:
            prefixed_name = f"{arch}_{repo_name}"
        if logger:
            logger.info(f"Auto-prefixed repo_name with architecture and OS: {prefixed_name}")
        return prefixed_name
    return repo_name


def _update_existing_line(line: str, package_name: str, package_type: str, status: str,
                          repo_name: str, status_file_path: str, catalog_name: str = "") -> str:
    """Update an existing line in status file.

    Args:
        line: Existing line content
        package_name: Package name to match
        package_type: Package type
        status: New status
        repo_name: Repository name
        status_file_path: Path for architecture extraction
        catalog_name: Catalog name for multi-catalog tracking

    Returns:
        str: Updated line content
    """
    parts = line.strip().split(',')
    final_repo_name = _prefix_repo_name_with_arch(repo_name, status_file_path, None)
    if len(parts) >= 5:
        parts[2] = final_repo_name if final_repo_name else ''
        parts[3] = status
        parts[4] = catalog_name
        return ','.join(parts) + '\n'
    if len(parts) >= 4:
        parts[2] = final_repo_name if final_repo_name else ''
        parts[3] = status
        parts.append(catalog_name)
        return ','.join(parts) + '\n'

    # Handle short lines
    repo_val = final_repo_name if final_repo_name else ''
    return f"{package_name},{package_type},{repo_val},{status},{catalog_name}\n"


def write_status_to_file(status_file_path, package_name, package_type, status,
                          logger, file_lock: Lock, repo_name=None,
                          catalog_name=""):
    """
    Writes or updates the status of a package in the status file.
    Also updates pulp_mirror_index.json with the package status.

    Args:
        status_file_path: Path to the status file
        package_name: Name of the package
        package_type: Type of the package (rpm, image, etc.)
        status: Status (Success, Failed, etc.)
        logger: Logger instance
        file_lock: Lock for thread safety
        repo_name: Optional repository name (for RPMs)
        catalog_name: Optional catalog name for multi-catalog tracking
    """
    logger.info("#" * 30 + f" {write_status_to_file.__name__} start " + "#" * 30)

    # Auto-prefix repo_name with architecture if needed
    repo_name = _prefix_repo_name_with_arch(repo_name, status_file_path, logger)

    try:
        with file_lock:  # Ensure only one process can write at a time
            if os.path.exists(status_file_path):
                _update_existing_file(status_file_path, package_name, package_type,
                                       status, repo_name, catalog_name)
            else:
                _create_new_file(status_file_path, package_name, package_type,
                                  status, repo_name, catalog_name)

            logger.info(f"Status written to {status_file_path} for {package_name}.")

            # Update pulp_mirror_index.json
            _update_mirror_index_for_package(
                status_file_path, package_name, package_type, status,
                repo_name, catalog_name, logger
            )
    except OSError as e:
        logger.error(f"Failed to write to status file: {status_file_path}. Error: {str(e)}")
        raise RuntimeError(
            f"Failed to write to status file: {status_file_path}. Error: {str(e)}"
        ) from e
    finally:
        logger.info("#" * 30 + f" {write_status_to_file.__name__} end " + "#" * 30)


def _update_existing_file(status_file_path, package_name, package_type, status,
                           repo_name, catalog_name=""):
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
                    line, package_name, package_type, status, repo_name,
                    status_file_path, catalog_name
                )
                f.write(updated_line)
                updated = True
            else:
                f.write(line)

        if not updated:
            final_repo_name = _prefix_repo_name_with_arch(
                repo_name, status_file_path, None)
            repo_val = final_repo_name if final_repo_name else ''
            f.write(
                f"{package_name},{package_type},{repo_val},{status},{catalog_name}\n")


def _create_new_file(status_file_path, package_name, package_type, status,
                      repo_name, catalog_name=""):
    """Create new status file with package status."""
    with open(status_file_path, "w", encoding='utf-8') as f:
        f.write(STATUS_CSV_HEADER)
        final_repo_name = _prefix_repo_name_with_arch(
            repo_name, status_file_path, None)
        repo_val = final_repo_name if final_repo_name else ''
        f.write(
            f"{package_name},{package_type},{repo_val},{status},{catalog_name}\n")


def _update_mirror_index_for_package(status_file_path, package_name, package_type,
                                      status, repo_name, catalog_name, logger):
    """
    Update pulp_mirror_index.json when a package status is written to status.csv.

    Args:
        status_file_path: Path to the status file (used to derive mirror_index path)
        package_name: Name of the package
        package_type: Type of the package (rpm, image, etc.)
        status: Status (Success, Failed, etc.)
        repo_name: Repository name (for RPMs)
        catalog_name: Catalog name
        logger: Logger instance
    """
    try:
        # Derive pulp_mirror_index.json path from status_file_path
        # Expected path: .../rhel/10.0/x86_64/software_name/status.csv
        # Mirror index: .../rhel/10.0/mirror_status/pulp_mirror_index.json

        path_parts = status_file_path.split(os.sep)

        # Find the OS type and version in the path
        os_type_idx = -1
        for i, part in enumerate(path_parts):
            if part in ['rhel']:
                os_type_idx = i
                break

        if os_type_idx == -1 or os_type_idx + 1 >= len(path_parts):
            logger.debug(f"Could not derive mirror_index path from {status_file_path}")
            return

        # Construct mirror_index path
        base_path = os.sep.join(path_parts[:os_type_idx + 2])
        mirror_index_path = os.path.join(base_path, "mirror_status", "pulp_mirror_index.json")

        if not os.path.exists(mirror_index_path):
            logger.debug(
                f"Mirror index not found at {mirror_index_path}, skipping update")
            return

        # Load mirror index
        mirror_data = load_mirror_index(mirror_index_path, logger)
        if not mirror_data:
            logger.warning(f"Failed to load mirror index from {mirror_index_path}")
            return

        # Check if package exists in mirror index
        packages = mirror_data["MirrorIndex"].get("packages", {})

        # For images, the package_name in status.csv includes tag
        # but mirror_index.json stores it without tag
        # Try to find the package with and without tag
        package_key = package_name
        if package_type == "image" and package_name not in packages:
            # Try removing tag/version after last colon
            if ':' in package_name:
                package_key = package_name.rsplit(':', 1)[0]
                logger.debug(
                    f"Image package '{package_name}' not found, "
                    f"trying without tag: '{package_key}'")

        if package_key not in packages:
            logger.debug(
                f"Package '{package_name}' (key: '{package_key}') "
                f"not found in mirror index, skipping update")
            return

        # Map status.csv status to mirror index status
        # status.csv: "Success" or "Failed"
        # mirror_index: "mirrored", "failed", or "pending"
        mirror_status = "mirrored" if status == "Success" else "failed"
        error_msg = "" if status == "Success" else "Package download/verification failed"

        # Get package info from mirror index
        pkg_info = packages[package_key]

        # Update mirror index entry
        update_mirror_index_entry(
            mirror_data=mirror_data,
            package_name=package_key,
            pkg_type=package_type,
            version=pkg_info.get("version", ""),
            arch=pkg_info.get("arch", ""),
            composite_hash=pkg_info.get("hash", ""),
            source=pkg_info.get("source", ""),
            catalogs=pkg_info.get("catalogs", [catalog_name] if catalog_name else []),
            status=mirror_status,
            error=error_msg,
            repo_name=repo_name or pkg_info.get("repo_name", "")
        )

        # Save updated mirror index
        save_mirror_index(mirror_index_path, mirror_data, logger)
        logger.debug(
            f"Updated mirror index for package '{package_key}' "
            f"(original: '{package_name}') with status '{mirror_status}'")

    except Exception as exc:  # pylint: disable=broad-exception-caught
        # Don't fail the main operation if mirror index update fails
        logger.warning(
            f"Failed to update mirror index for package '{package_name}': {exc}")
