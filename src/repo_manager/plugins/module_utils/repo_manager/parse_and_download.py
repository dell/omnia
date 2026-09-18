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
import shlex
import tempfile
from multiprocessing import Lock
from ansible.module_utils.repo_manager.config import (
    ARCH_SUFFIXES,
    PULP_CLI_EXECUTABLE,
    STATUS_CSV_HEADER,
)
from ansible.module_utils.repo_manager.mirror_status import (
    load_mirror_index,
    save_mirror_index,
    update_mirror_index_entry,
    find_mirror_entry,
)
from ansible.module_utils.repo_manager.security_utils import (
    mask_sensitive_data,
    redact_sensitive_output,
)


_SHARED_STATUS_FILE_LOCK = None


def configure_status_file_lock(file_lock):
    """Configure the process-safe lock supplied by the parent worker manager."""
    global _SHARED_STATUS_FILE_LOCK  # pylint: disable=global-statement
    _SHARED_STATUS_FILE_LOCK = file_lock


def _atomic_write_lines(destination, lines):
    """Durably replace a text file using a unique temporary file beside it."""
    directory = os.path.dirname(destination) or "."
    os.makedirs(directory, exist_ok=True)
    file_descriptor, temp_path = tempfile.mkstemp(
        prefix=f".{os.path.basename(destination)}.", suffix=".tmp", dir=directory
    )
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as file:
            file.writelines(lines)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, destination)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def execute_command(command, logger, type_json=False, enhanced_error_info=False):  # pylint: disable=too-many-return-statements
    """
    Executes a command and captures the output (both stdout and stderr).

    Always uses shell=False with list arguments to avoid shell injection risks.
    Commands are parsed using shlex.split() to handle proper argument separation.

    Args:
        command (str or list): The command to execute.
        logger (logging.Logger): Logger instance for logging the process and errors.
        type_json (bool): If True, attempts to parse stdout as JSON.
        enhanced_error_info (bool): If True, return dict on failure instead of False.

    Returns:
        Success: dict with returncode, stdout, stderr
        Failure (enhanced_error_info=False): False
        Failure (enhanced_error_info=True): dict with returncode, stdout, stderr, success=False
    """
    logger.info(f"--- {execute_command.__name__} START ---")
    status = {}
    safe_cmd_string = "<command omitted>"

    try:
        # Mask sensitive info before logging
        safe_cmd_string = mask_sensitive_data(command)
        logger.info(f"Executing command: {safe_cmd_string}")

        # Always use shell=False with list arguments to avoid shell injection.
        cmd_args = (
            [str(value) for value in command]
            if isinstance(command, (list, tuple))
            else shlex.split(command)
        )
        if cmd_args and cmd_args[0] == "pulp":
            cmd_args[0] = PULP_CLI_EXECUTABLE

        # Run the command with list arguments
        cmd = subprocess.run(
            cmd_args,
            universal_newlines=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            check=False
        )
        status["returncode"] = cmd.returncode
        status["stdout"] = cmd.stdout.strip() if cmd.stdout else None
        status["stderr"] = (
            redact_sensitive_output(cmd.stderr.strip(), command) if cmd.stderr else None
        )
        status["success"] = cmd.returncode == 0

        if cmd.returncode != 0:
            logger.error(f"Command failed (rc={cmd.returncode})")
            if status['stderr'] and status['stderr'].strip():
                logger.error(f"STDERR: {status['stderr'].strip()}")

            if enhanced_error_info:
                return status  # Dict with error details
            return False  # Existing behavior

        if type_json:
            if not status["stdout"]:
                logger.error(
                    "Command succeeded but returned empty output when JSON was expected")
                if enhanced_error_info:
                    status["success"] = False
                    return status
                return False
            try:
                status["stdout"] = json.loads(status["stdout"])
            except json.JSONDecodeError:
                logger.error("Command returned invalid JSON output")
                if enhanced_error_info:
                    status["success"] = False
                    return status
                return False

        logger.info("Command succeeded.")
        return status
    except subprocess.CalledProcessError:
        logger.error("Command failed: %s", safe_cmd_string)
        return False
    except subprocess.TimeoutExpired:
        logger.error("Command timed out: %s", safe_cmd_string)
        if enhanced_error_info:
            return {"success": False, "returncode": -1,
                    "stdout": None, "stderr": "Command timed out"}
        return False
    except OSError:
        logger.error("OS error during command: %s", safe_cmd_string)
        if enhanced_error_info:
            return {"success": False, "returncode": -1,
                    "stdout": None, "stderr": "Unable to execute command"}
        return False

    finally:
        logger.info(f"--- {execute_command.__name__} END ---")


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
        parts[1] = package_type
        parts[2] = final_repo_name if final_repo_name else ''
        parts[3] = status
        parts[4] = catalog_name
        return ','.join(parts) + '\n'
    if len(parts) >= 4:
        parts[1] = package_type
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
        file_lock: Backward-compatible local lock used outside parallel workers
        repo_name: Optional repository name (for RPMs)
        catalog_name: Optional catalog name for multi-catalog tracking
    """
    logger.info(f"--- {write_status_to_file.__name__} START ---")

    # Auto-prefix repo_name with architecture if needed
    repo_name = _prefix_repo_name_with_arch(repo_name, status_file_path, logger)

    try:
        effective_lock = _SHARED_STATUS_FILE_LOCK or file_lock
        with effective_lock:
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
    except OSError as error:
        logger.error("Failed to update the package status file")
        raise RuntimeError(
            "Failed to update the package status file"
        ) from error
    finally:
        logger.info(f"--- {write_status_to_file.__name__} END ---")


def _update_existing_file(status_file_path, package_name, package_type, status,
                           repo_name, catalog_name=""):
    """Update existing status file with new package status using atomic write."""
    # Read existing content
    if os.path.exists(status_file_path):
        with open(status_file_path, "r", encoding='utf-8') as f:
            lines = f.readlines()
    else:
        lines = [STATUS_CSV_HEADER]

    # Update in memory
    updated = False
    for i, line in enumerate(lines):
        if line.startswith(f"{package_name},"):
            lines[i] = _update_existing_line(
                line, package_name, package_type, status, repo_name,
                status_file_path, catalog_name
            )
            updated = True
            break

    if not updated:
        final_repo_name = _prefix_repo_name_with_arch(
            repo_name, status_file_path, None)
        repo_val = final_repo_name if final_repo_name else ''
        lines.append(
            f"{package_name},{package_type},{repo_val},{status},{catalog_name}\n")

    _atomic_write_lines(status_file_path, lines)


def _create_new_file(status_file_path, package_name, package_type, status,
                      repo_name, catalog_name=""):
    """Create new status file with package status using atomic write."""
    # Build content in memory
    final_repo_name = _prefix_repo_name_with_arch(
        repo_name, status_file_path, None)
    repo_val = final_repo_name if final_repo_name else ''
    lines = [
        STATUS_CSV_HEADER,
        f"{package_name},{package_type},{repo_val},{status},{catalog_name}\n"
    ]

    _atomic_write_lines(status_file_path, lines)


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
        # Expected path:
        # .../<os>/<version>/<arch>/<software>/status.csv
        os_type, os_version = get_os_info_from_status_path(status_file_path)
        if not os_type or not os_version:
            logger.debug(f"Could not derive mirror_index path from {status_file_path}")
            return

        version_log_path = os.path.dirname(
            os.path.dirname(os.path.dirname(status_file_path))
        )
        mirror_index_path = os.path.join(
            version_log_path, "mirror_status", "pulp_mirror_index.json"
        )

        if not os.path.exists(mirror_index_path):
            logger.debug(
                f"Mirror index not found at {mirror_index_path}, skipping update")
            return

        # Load mirror index
        mirror_data = load_mirror_index(mirror_index_path, logger)
        if not mirror_data:
            logger.warning(f"Failed to load mirror index from {mirror_index_path}")
            return

        arch = get_arch_from_status_path(status_file_path)
        identity_key, pkg_info = find_mirror_entry(
            mirror_data, package_name, package_type, arch
        )
        if identity_key is None:
            logger.debug(
                "No unique mirror identity found for package '%s' "
                "(type=%s, arch=%s); skipping update",
                package_name, package_type, arch
            )
            return

        # Map status.csv status to mirror index status
        # status.csv: "Success" or "Failed"
        # mirror_index: "mirrored", "failed", or "pending"
        mirror_status = "mirrored" if status == "Success" else "failed"
        error_msg = "" if status == "Success" else "Package download/verification failed"

        # Update mirror index entry
        update_mirror_index_entry(
            mirror_data=mirror_data,
            package_name=pkg_info.get("package_name", package_name),
            pkg_type=pkg_info.get("type", package_type),
            version=pkg_info.get("version", ""),
            arch=pkg_info.get("arch", arch),
            composite_hash=identity_key,
            source=pkg_info.get("source", ""),
            catalogs=pkg_info.get("catalogs", [catalog_name] if catalog_name else []),
            status=mirror_status,
            error=error_msg,
            repo_name=repo_name or pkg_info.get("repo_name", "")
        )

        # Save updated mirror index
        save_mirror_index(mirror_index_path, mirror_data, logger)
        logger.debug(
            f"Updated mirror index identity '{identity_key}' "
            f"(original: '{package_name}') with status '{mirror_status}'")

    except Exception as exc:  # pylint: disable=broad-exception-caught
        # Don't fail the main operation if mirror index update fails
        logger.warning(
            f"Failed to update mirror index for package '{package_name}': {exc}")
