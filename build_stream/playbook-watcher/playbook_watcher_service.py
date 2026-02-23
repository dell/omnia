#!/usr/bin/env python3
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

"""Playbook Watcher Service for OIM Core Container.

This service monitors the NFS playbook request queue, executes Ansible playbooks,
and writes results back to the results queue. It is designed to be stateless and
run as a systemd service in the OIM Core container.

Architecture:
- Polls /opt/omnia/build_stream/playbook_queue/requests/ every 2 seconds
- Moves requests to processing/ to prevent duplicate execution
- Executes ansible-playbook with timeout and error handling
- Writes structured results to /opt/omnia/build_stream/playbook_queue/results/
- Supports max 5 concurrent playbook executions
"""

import json
import logging
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread, Semaphore
from typing import Dict, Optional, Any, List

# Implicit logging utilities for secure logging
def log_secure_info(level: str, message: str, identifier: Optional[str] = None) -> None:
    """Log information securely with optional identifier truncation.
    
    This function provides consistent secure logging across all modules.
    When an identifier is provided, only the first 8 characters are logged
    to prevent exposure of sensitive data while maintaining debugging capability.
    
    Args:
        level: Log level ('info', 'warning', 'error', 'debug', 'critical')
        message: Log message template
        identifier: Optional identifier (job_id, request_id, etc.) - first 8 chars logged
    """
    logger = logging.getLogger(__name__)

    if identifier:
        # Always log first 8 characters for identification
        log_message = f"{message}: {identifier[:8]}..."
    else:
        # Generic message when no identifier context
        log_message = message

    log_func = getattr(logger, level)
    log_func(log_message)

# Configuration
QUEUE_BASE = Path(os.getenv("PLAYBOOK_QUEUE_BASE", ""))
REQUESTS_DIR = QUEUE_BASE / "requests"
RESULTS_DIR = QUEUE_BASE / "results"
PROCESSING_DIR = QUEUE_BASE / "processing"
ARCHIVE_DIR = QUEUE_BASE / "archive"

# NFS shared path configuration
NFS_SHARE_PATH = Path(os.getenv("NFS_SHARE_PATH", ""))
HOST_LOG_BASE_DIR = NFS_SHARE_PATH / "omnia" / "log" / "build_stream"
CONTAINER_LOG_BASE_DIR = Path("/opt/omnia/log/build_stream")

POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "2"))
MAX_CONCURRENT_JOBS = int(os.getenv("MAX_CONCURRENT_JOBS", "5"))
DEFAULT_TIMEOUT_MINUTES = int(os.getenv("DEFAULT_TIMEOUT_MINUTES", "30"))

# Playbook name to full path mapping - prevents injection from user input
PLAYBOOK_NAME_TO_PATH = {
    "include_input_dir.yml": "/omnia/utils/include_input_dir.yml",
    "build_image_aarch64.yml": "/omnia/build_image_aarch64/build_image_aarch64.yml",
    "build_image_x86_64.yml": "/omnia/build_image_x86_64/build_image_x86_64.yml",
    "discovery.yml": "/omnia/discovery/discovery.yml",
    "local_repo.yml": "/omnia/local_repo/local_repo.yml",
}

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("playbook_watcher")

# Global state
SHUTDOWN_REQUESTED = False
job_semaphore = Semaphore(MAX_CONCURRENT_JOBS)


def signal_handler(signum, _):
    """Handle shutdown signals gracefully."""
    global SHUTDOWN_REQUESTED
    log_secure_info(
        "info",
        "Received signal",
        str(signum)
    )
    SHUTDOWN_REQUESTED = True


def ensure_directories():
    """Ensure all required directories exist with proper permissions."""
    directories = [
        REQUESTS_DIR,
        RESULTS_DIR,
        PROCESSING_DIR,
        ARCHIVE_DIR,
        ARCHIVE_DIR / "requests",
        ARCHIVE_DIR / "results",
        HOST_LOG_BASE_DIR,  # NFS log directory
    ]

    for directory in directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            log_secure_info(
                "debug",
                "Ensured directory exists"
            )
        except (OSError, IOError) as e:
            log_secure_info(
                "error",
                "Failed to create directory"
            )
            raise


def validate_playbook_name(playbook_name: str) -> bool:
    """Validate playbook name against the allowed whitelist.
    
    Args:
        playbook_name: Name of the playbook file (without path)
        
    Returns:
        True if name is in the whitelist, False otherwise
    """
    # Ensure it's a playbook name (no slash)
    if '/' in playbook_name:
        log_secure_info(
            "error",
            "Playbook name cannot contain path separators",
            playbook_name[:8] if playbook_name else None
        )
        return False
        
    # Check if it's in our mapping
    if playbook_name in PLAYBOOK_NAME_TO_PATH:
        return True
    
    # Log the rejection
    log_secure_info(
        "error",
        "Playbook name not in allowed whitelist",
        playbook_name[:8] if playbook_name else None
    )
    return False


def map_playbook_name_to_path(playbook_name: str) -> Optional[str]:
    """Validate playbook name and map it to the full path.
    
    Args:
        playbook_name: Name of the playbook file (untrusted input)
        
    Returns:
        The full path if valid, None if invalid
    """
    # Validate the playbook name
    if not validate_playbook_name(playbook_name):
        return None
        
    # Map the name to full path
    full_path = PLAYBOOK_NAME_TO_PATH[playbook_name]
    
    # Return a new string instance to break the taint chain
    return str(full_path)


def validate_job_id(job_id: str) -> bool:
    """Validate job ID format.
    
    Args:
        job_id: Job identifier
        
    Returns:
        True if valid, False otherwise
    """
    # Allow UUID format or alphanumeric with hyphens/underscores
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    alnum_pattern = r'^[a-zA-Z0-9_-]+$'
    
    return bool(re.match(uuid_pattern, job_id) or re.match(alnum_pattern, job_id))


def validate_stage_name(stage_name: str) -> bool:
    """Validate stage name to prevent injection.
    
    Args:
        stage_name: Name of the stage
        
    Returns:
        True if valid, False otherwise
    """
    # Only allow alphanumeric, spaces, hyphens, and underscores
    pattern = r'^[a-zA-Z0-9 _-]+$'
    return bool(re.match(pattern, stage_name))


def validate_command(cmd: list, playbook_path: str, extra_vars_json: str = None) -> bool:
    """Validate command structure and arguments to prevent injection.
    
    This function implements strict command allowlisting with rigorous validation
    of each command argument to prevent any possibility of command injection.
    
    Args:
        cmd: Command list to validate
        playbook_path: Expected playbook path (already validated)
        extra_vars_json: Not used, kept for backward compatibility
        
    Returns:
        True if valid, raises ValueError with detailed message if invalid
    """
    # Define the allowlisted command structure
    # This defines the exact structure and position of each argument
    ALLOWED_CMD_STRUCTURE = [
        {"value": "podman", "fixed": True},
        {"value": "exec", "fixed": True},
        {"value": "-e", "fixed": True},
        {"value": "ANSIBLE_LOG_PATH=", "prefix": True},  # Only the prefix is fixed, value is validated separately
        {"value": "omnia_core", "fixed": True},
        {"value": "ansible-playbook", "fixed": True},
        {"value": None, "fixed": False},  # playbook_path (validated separately)
        {"value": "-v", "fixed": True}
    ]
    
    # 1. Length check - command must have exactly the expected number of arguments
    if len(cmd) != len(ALLOWED_CMD_STRUCTURE):
        log_secure_info(
            "error",
            "Command structure length mismatch",
            f"Expected {len(ALLOWED_CMD_STRUCTURE)}, got {len(cmd)}"
        )
        raise ValueError("Invalid command structure")
    
    # 2. Structure validation - each argument must match the allowlisted structure
    for i, (arg, allowed) in enumerate(zip(cmd, ALLOWED_CMD_STRUCTURE)):
        # Type check - must be string
        if not isinstance(arg, str):
            log_secure_info(
                "error",
                "Non-string argument in command",
                f"Position: {i}"
            )
            raise ValueError("Invalid command argument type")
        
        # Length check - prevent excessively long arguments
        if len(arg) > 4096:  # Reasonable maximum length
            log_secure_info(
                "error",
                "Command argument exceeds maximum allowed length",
                f"Position: {i}, Length: {len(arg)}"
            )
            raise ValueError("Command argument too long")
            
        # Fixed arguments must match exactly
        if allowed.get("fixed", False) and arg != allowed.get("value", ""):
            log_secure_info(
                "error",
                f"Command argument at position {i} does not match allowlist",
                f"Expected '{allowed.get('value', '')}', got '{arg}'"
            )
            raise ValueError(f"Invalid command argument at position {i}")
        
        # Arguments with prefix must start with the specified prefix
        if allowed.get("prefix") and not arg.startswith(allowed.get("value", "")):
            log_secure_info(
                "error",
                f"Command argument at position {i} does not start with required prefix",
                f"Expected prefix '{allowed.get('value', '')}', got '{arg}'"
            )
            raise ValueError(f"Invalid command argument prefix at position {i}")
            
        # Special validation for playbook path
        if not allowed.get("fixed", True) and i == 6:  # playbook_path position
            if arg != playbook_path:
                log_secure_info(
                    "error",
                    "Playbook path in command does not match validated path"
                )
                raise ValueError("Playbook path mismatch")
    
    # 3. Character validation - check for dangerous characters in all arguments
    DANGEROUS_CHARS = ['\n', '\r', '\0', '\t', '\v', '\f', '\a', '\b', '\\', '`', '$', '&', '|', ';', '<', '>', '(', ')', '*', '?', '~', '#']
    
    # Skip validation for playbook path position
    SKIP_POSITIONS = [6]  # Position of playbook_path
    
    for i, arg in enumerate(cmd):
        # Skip validation for playbook path
        if i in SKIP_POSITIONS:
            continue
            
        for char in DANGEROUS_CHARS:
            if char in arg:
                log_secure_info(
                    "error",
                    "Dangerous character detected in command argument",
                    f"Position: {i}, Character: {repr(char)}"
                )
                raise ValueError("Invalid command argument content")
    
    # 4. Shell binary check - prevent shell execution
    SHELL_BINARIES = ["sh", "bash", "dash", "zsh", "ksh", "csh", "tcsh", "fish"]
    for i, arg in enumerate(cmd):
        if arg in SHELL_BINARIES:
            log_secure_info(
                "error",
                "Shell binary detected in command argument",
                f"Position: {i}, Value: {arg}"
            )
            raise ValueError("Shell binary not allowed in command")
    
    # 5. URL check - prevent remote resource fetching
    for i, arg in enumerate(cmd):
        if re.search(r'(https?|ftp|file)://', arg):
            log_secure_info(
                "error",
                "URL detected in command argument",
                f"Position: {i}, Value: {arg[:8]}"
            )
            raise ValueError("URLs not allowed in command arguments")
    
    return True


# validate_extra_vars function has been removed as we no longer use extra_vars
# This eliminates a potential security vulnerability



def parse_request_file(request_path: Path) -> Optional[Dict[str, Any]]:
    """Parse and validate request file.

    Args:
        request_path: Path to the request JSON file

    Returns:
        Parsed request dictionary or None if invalid
    """
    try:
        # Validate file path to prevent directory traversal
        request_path_str = str(request_path)
        if '..' in request_path_str or not request_path_str.startswith('/'):
            log_secure_info(
                "error",
                "Invalid request file path: possible directory traversal",
                request_path_str[:8]
            )
            return None
            
        # Ensure file exists and is a regular file
        if not os.path.isfile(request_path):
            log_secure_info(
                "error",
                "Request path is not a regular file",
                request_path_str[:8]
            )
            return None
            
        with open(request_path, 'r', encoding='utf-8') as f:
            try:
                request_data = json.load(f)
            except json.JSONDecodeError:
                log_secure_info(
                    "error",
                    "Invalid JSON in request file",
                    request_path_str[:8]
                )
                return None
                
        # Validate data type
        if not isinstance(request_data, dict):
            log_secure_info(
                "error",
                "Request data is not a dictionary",
                request_path_str[:8]
            )
            return None

        # Validate required fields
        required_fields = ["job_id", "stage_name", "playbook_path"]
        missing_fields = [field for field in required_fields if field not in request_data]

        if missing_fields:
            logger.error(
                "Request file missing required fields: %s",
                ', '.join(missing_fields)
            )
            return None

        # Validate inputs to prevent injection
        job_id = str(request_data["job_id"])
        stage_name = str(request_data["stage_name"])
        playbook_name = str(request_data["playbook_path"])  # This is actually the playbook name
        
        if not validate_job_id(job_id):
            log_secure_info("error", "Invalid job_id format in request", job_id[:8])
            return None
            
        if not validate_stage_name(stage_name):
            log_secure_info("error", "Invalid stage_name format in request", stage_name[:8])
            return None
            
        # Map the playbook name to its full path
        # This returns the full path or None if validation fails
        full_playbook_path = map_playbook_name_to_path(playbook_name)
        if full_playbook_path is None:
            log_secure_info("error", "Invalid or unknown playbook name in request", playbook_name[:8])
            return None

        # Set defaults
        request_data.setdefault("correlation_id", job_id)
        
        # Store both the original playbook name and the mapped full path
        # The full path will be used for command execution
        request_data["playbook_name"] = playbook_name
        request_data["full_playbook_path"] = full_playbook_path

        log_secure_info(
            "info",
            "Parsed request for job",
            job_id
        )
        log_secure_info(
            "debug",
            "Stage name",
            stage_name
        )

        return request_data

    except json.JSONDecodeError as e:
        log_secure_info(
            "error",
            "Invalid JSON in request file"
        )
        return None
    except (KeyError, TypeError, ValueError) as e:
        log_secure_info(
            "error",
            "Error parsing request file"
        )
        return None


def extract_playbook_name(full_playbook_path: str) -> str:
    """Extract the playbook name from the full path.
    
    Args:
        full_playbook_path: Full path to the playbook file
        
    Returns:
        The playbook name (filename without path)
    """
    # Get the basename (filename with extension)
    return os.path.basename(full_playbook_path)


def _build_log_paths(playbook_path: str, started_at: datetime) -> tuple:
    """Build host and container log file paths without job_id.

    Args:
        playbook_path: Full path to the playbook file
        started_at: Start time for timestamp

    Returns:
        Tuple of (host_log_file_path, container_log_file_path, host_log_dir)
    """
    # Extract playbook name from the full path
    playbook_name = extract_playbook_name(playbook_path)
    
    # Create base log directory on NFS share (no job-specific subdirectory)
    host_log_dir = HOST_LOG_BASE_DIR
    host_log_dir.mkdir(parents=True, exist_ok=True)

    # Create log file path with playbook name and timestamp only (no job_id)
    timestamp = started_at.strftime("%Y%m%d_%H%M%S")
    host_log_file_path = host_log_dir / f"{playbook_name}_{timestamp}.log"

    # Container log path (equivalent path in container)
    container_log_file_path = (
        CONTAINER_LOG_BASE_DIR / f"{playbook_name}_{timestamp}.log"
    )

    return host_log_file_path, container_log_file_path, host_log_dir


def move_log_to_job_directory(host_log_file_path: Path, job_id: str) -> Path:
    """Move log file to a job-specific directory after completion.
    
    Args:
        host_log_file_path: Current path of the log file
        job_id: Job identifier for creating the job directory
        
    Returns:
        New path of the log file in the job directory
    """
    # Create job-specific directory
    job_dir = HOST_LOG_BASE_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    # Get the log filename
    log_filename = host_log_file_path.name
    
    # New path in job directory
    new_log_path = job_dir / log_filename
    
    # Move the log file
    try:
        shutil.move(str(host_log_file_path), str(new_log_path))
        log_secure_info(
            "info",
            "Log file moved to job directory",
            job_id[:12] if job_id else ""
        )
    except (OSError, IOError) as e:
        log_secure_info(
            "error",
            "Failed to move log file to job directory"
        )
        # Return original path if move fails
        return host_log_file_path
    
    return new_log_path


def execute_playbook(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Execute Ansible playbook and capture results.

    Args:
        request_data: Parsed request dictionary

    Returns:
        Result dictionary with execution details
    """
    job_id = request_data["job_id"]
    stage_name = request_data["stage_name"]
    # Use the full_playbook_path which is the mapped full path from playbook name
    playbook_path = request_data["full_playbook_path"]
    playbook_name = request_data["playbook_name"]  # Original playbook name for logging
    # Use default timeout to prevent potential injection from user input
    timeout_minutes = DEFAULT_TIMEOUT_MINUTES
    correlation_id = request_data.get("correlation_id", job_id)

    log_secure_info(
        "info",
        "Executing playbook for job",
        job_id
    )
    log_secure_info(
        "debug",
        "Stage name",
        stage_name
    )
    log_secure_info(
        "debug",
        "Playbook name",
        playbook_name
    )

    started_at = datetime.now(timezone.utc)
    host_log_file_path, container_log_file_path, _ = _build_log_paths(
        playbook_path, started_at
    )

    # Build podman command to execute playbook in omnia_core container
    # Build command as a list to prevent shell injection
    # Ensure environment variable value is properly sanitized
    log_path_str = str(container_log_file_path)
    
    # Strict validation for log path
    if not log_path_str.startswith('/') or '..' in log_path_str:
        log_secure_info(
            "error",
            "Container log path must be absolute and cannot contain path traversal",
            log_path_str[:8]
        )
        raise ValueError("Invalid container log path")
        
    # Validate log path format using regex (alphanumeric, underscore, hyphen, forward slash, and dots)
    if not re.match(r'^[a-zA-Z0-9_\-/.]+$', log_path_str):
        log_secure_info(
            "error",
            "Container log path contains invalid characters",
            log_path_str[:8]
        )
        raise ValueError("Invalid container log path format")
    
    # Build command as a list to prevent shell injection
    # We no longer use extra_vars to prevent potential command injection
    # This simplifies the code and removes a potential security vulnerability
    
    # Command structure will be validated by the validate_command function
    
    # Build command as a list with all validated components
    # Each element is a separate argument - no shell interpretation possible
    cmd = [
        "podman", "exec",
        "-e", f"ANSIBLE_LOG_PATH={log_path_str}",
        "omnia_core",
        "ansible-playbook",
        playbook_path,  # Validated against strict whitelist
        "-v"
    ]
    
    # Use the dedicated command validation function to perform comprehensive validation
    # This includes structure validation, argument validation, and security checks
    try:
        validate_command(cmd, playbook_path)
    except ValueError as e:
        log_secure_info(
            "error",
            "Command validation failed",
            str(e)
        )
        raise ValueError(f"Command validation failed: {e}")

    # Don't log the full command with potentially sensitive paths
    log_secure_info(
        "debug",
        "Executing ansible playbook for job",
        job_id
    )
    log_secure_info(
        "info",
        "Ansible logs will be written to job directory",
        job_id
    )

    try:
        # Execute playbook with timeout and custom log path
        timeout_seconds = timeout_minutes * 60
        # Only set ANSIBLE_LOG_PATH in the environment
        # This is already passed as -e parameter to podman exec
        # No need for a full sanitized environment
        
        # Log the command being executed (without sensitive details)
        log_secure_info(
            "debug",
            "Executing command",
            f"podman exec omnia_core ansible-playbook [playbook]"
        )
        
        # Execute with explicit shell=False and validated arguments
        result = subprocess.run(
            cmd,
            capture_output=False,  # Don't capture to avoid duplication with ANSIBLE_LOG_PATH
            timeout=timeout_seconds,
            check=False,
            shell=False,  # Explicitly set shell=False to prevent injection
            text=False,   # Don't interpret output as text to prevent encoding issues
            start_new_session=True  # Isolate the process from the parent session
        )

        # Log file is directly accessible via NFS share, no need to copy
        # Wait a moment for log to be written
        time.sleep(0.5)

        # Verify log file exists
        if host_log_file_path.exists():
            log_secure_info(
                "info",
                "Log file confirmed for job",
                job_id
            )
            # Move log file to job-specific directory after completion
            host_log_file_path = move_log_to_job_directory(host_log_file_path, job_id)
        else:
            log_secure_info(
                "warning",
                "Log file not found at expected location for job",
                job_id
            )

        completed_at = datetime.now(timezone.utc)
        duration_seconds = (completed_at - started_at).total_seconds()

        # Determine status
        status = "success" if result.returncode == 0 else "failed"

        log_secure_info(
            "info",
            "Playbook execution completed for job",
            job_id
        )
        log_secure_info(
            "debug",
            "Execution status",
            status
        )

        # Build result dictionary
        result_data = {
            "job_id": job_id,
            "stage_name": stage_name,
            "request_id": request_data.get("request_id", job_id),
            "correlation_id": correlation_id,
            "status": status,
            "exit_code": result.returncode,
            "log_file_path": str(host_log_file_path),  # Host path to Ansible log file (NFS share)
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_seconds": int(duration_seconds),
            "timestamp": completed_at.isoformat(),
        }

        # Add error details if failed
        if status == "failed":
            result_data["error_code"] = "PLAYBOOK_EXECUTION_FAILED"
            result_data["error_summary"] = f"Playbook exited with code {result.returncode}"

        return result_data

    except subprocess.TimeoutExpired:
        completed_at = datetime.now(timezone.utc)
        duration_seconds = (completed_at - started_at).total_seconds()

        log_secure_info(
            "error",
            "Playbook execution timed out for job",
            job_id
        )

        return {
            "job_id": job_id,
            "stage_name": stage_name,
            "request_id": request_data.get("request_id", job_id),
            "correlation_id": correlation_id,
            "status": "failed",
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Playbook execution timed out after {timeout_minutes} minutes",
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_seconds": int(duration_seconds),
            "error_code": "PLAYBOOK_TIMEOUT",
            "error_summary": f"Execution exceeded timeout of {timeout_minutes} minutes",
            "timestamp": completed_at.isoformat(),
        }

    except (OSError, subprocess.SubprocessError) as e:
        completed_at = datetime.now(timezone.utc)
        duration_seconds = (completed_at - started_at).total_seconds()

        logger.exception(
            "Unexpected error executing playbook for job %s",
            job_id
        )

        return {
            "job_id": job_id,
            "stage_name": stage_name,
            "request_id": request_data.get("request_id", job_id),
            "correlation_id": correlation_id,
            "status": "failed",
            "exit_code": -1,
            "stdout": "",
            "stderr": str(e),
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_seconds": int(duration_seconds),
            "error_code": "SYSTEM_ERROR",
            "error_summary": f"System error during execution: {str(e)}",
            "timestamp": completed_at.isoformat(),
        }

def write_result_file(result_data: Dict[str, Any], original_filename: str) -> bool:
    """Write result file to results directory.

    Args:
        result_data: Result dictionary to write
        original_filename: Original request filename for correlation

    Returns:
        True if successful, False otherwise
    """
    job_id = result_data["job_id"]

    try:
        # Use same filename pattern as request for easy correlation
        result_filename = original_filename
        result_path = RESULTS_DIR / result_filename

        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=2)

        log_secure_info(
            "info",
            "Wrote result file for job",
            job_id
        )
        return True

    except (OSError, IOError) as e:
        log_secure_info(
            "error",
            "Failed to write result file for job",
            job_id
        )
        return False

def archive_request_file(request_path: Path) -> None:
    """Archive processed request file.

    Args:
        request_path: Path to the request file to archive
    """
    try:
        archive_path = ARCHIVE_DIR / "requests" / request_path.name
        shutil.move(str(request_path), str(archive_path))
        log_secure_info(
            "debug",
            "Archived request file",
            request_path.name[:8] if request_path.name else None
        )
    except (OSError, IOError) as e:
        log_secure_info(
            "warning",
            "Failed to archive request file",
            request_path.name[:8] if request_path.name else None
        )

def process_request(request_path: Path) -> None:
    """Process a single request file.

    This function handles the complete lifecycle of a request:
    1. Move to processing directory (atomic lock)
    2. Parse request
    3. Execute playbook
    4. Write result
    5. Archive request

    Args:
        request_path: Path to the request file
    """
    request_filename = request_path.name
    processing_path = PROCESSING_DIR / request_filename

    with job_semaphore:

        try:
            # Move to processing directory (atomic lock)
            try:
                shutil.move(str(request_path), str(processing_path))
                log_secure_info(
                    "debug",
                    "Moved request to processing",
                    request_filename[:8] if request_filename else None
                )
            except FileNotFoundError:
                # File already moved by another process
                log_secure_info(
                    "debug",
                    "Request already being processed",
                    request_filename[:8] if request_filename else None
                )
                return

            # Parse request
            request_data = parse_request_file(processing_path)
            if not request_data:
                log_secure_info(
                    "error",
                    "Invalid request file",
                    request_filename[:8] if request_filename else None
                )
                # Write error result
                error_result = {
                    "job_id": "unknown",
                    "stage_name": "unknown",
                    "status": "failed",
                    "exit_code": -1,
                    "error_code": "INVALID_REQUEST",
                    "error_summary": "Failed to parse request file",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                write_result_file(error_result, request_filename)
                archive_request_file(processing_path)
                return

            # Execute playbook
            result_data = execute_playbook(request_data)

            # Write result
            write_result_file(result_data, request_filename)

            # Archive request
            archive_request_file(processing_path)

        finally:
            # Ensure processing file is cleaned up even on error
            if processing_path.exists():
                try:
                    processing_path.unlink()
                except (OSError, IOError) as e:
                    log_secure_info(
                        "warning",
                        "Failed to remove processing file",
                        request_filename[:8] if request_filename else None
                    )

def process_request_async(request_path: Path) -> None:
    """Process request in a separate thread.

    Args:
        request_path: Path to the request file
    """
    thread = Thread(target=process_request, args=(request_path,), daemon=True)
    thread.start()

def scan_and_process_requests() -> int:
    """Scan requests directory and process new requests.

    Returns:
        Number of requests processed
    """
    try:
        request_files = sorted(REQUESTS_DIR.glob("*.json"))

        if not request_files:
            return 0

        log_secure_info(
            "debug",
            "Found request files",
            str(len(request_files))
        )

        processed_count = 0
        for request_path in request_files:
            if SHUTDOWN_REQUESTED:
                log_secure_info(
                    "info",
                    "Shutdown requested"
                )
                break

            try:
                # Process asynchronously
                process_request_async(request_path)
                processed_count += 1
            except (OSError, IOError) as e:
                log_secure_info(
                    "error",
                    "Error processing request",
                    request_path.name[:8] if request_path.name else None
                )

        return processed_count

    except (OSError, IOError) as e:
        log_secure_info(
            "error",
            "Error scanning requests directory"
        )
        return 0

def run_watcher_loop():
    """Main watcher loop that continuously polls for requests."""
    log_secure_info(
        "info",
        "Starting Playbook Watcher Service"
    )
    log_secure_info(
        "info",
        "Queue base directory"
    )
    log_secure_info(
        "info",
        f"Poll interval: {POLL_INTERVAL_SECONDS}s"
    )
    log_secure_info(
        "info",
        f"Max concurrent jobs: {MAX_CONCURRENT_JOBS}"
    )
    log_secure_info(
        "info",
        f"Default timeout: {DEFAULT_TIMEOUT_MINUTES}m"
    )

    # Ensure directories exist
    try:
        ensure_directories()
    except (OSError, IOError) as e:
        log_secure_info(
            "critical",
            "Failed to initialize directories"
        )
        sys.exit(1)

    # Main loop
    iteration = 0
    while not SHUTDOWN_REQUESTED:
        iteration += 1

        try:
            processed_count = scan_and_process_requests()

            if processed_count > 0:
                log_secure_info(
                    "info",
                    "Processed requests in iteration",
                    str(processed_count)
                )

        except RuntimeError as e:
            logger.exception(
                "Unexpected error in watcher loop iteration %d",
                iteration
            )

        # Sleep before next poll
        time.sleep(POLL_INTERVAL_SECONDS)

    log_secure_info(
        "info",
        "Playbook Watcher Service stopped"
    )

def main():
    """Main entry point for the watcher service."""
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        run_watcher_loop()
    except KeyboardInterrupt:
        log_secure_info(
            "info",
            "Received keyboard interrupt"
        )
    except (RuntimeError, OSError):
        log_secure_info(
            "critical",
            "Fatal error in watcher service"
        )
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
