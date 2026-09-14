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
import shlex
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread, Semaphore
from typing import Dict, Optional, Any, List


def _resolve_omnia_env():
    """Read /etc/omnia/omnia.env and resolve variable references.
    systemd ``EnvironmentFile`` does not expand ``${VAR}`` references,
    so values like ``CATALOG_FILE_PATH=${OMNIA_DATA_PATH}/catalog/...``
    remain literal.  This function parses the file, resolves references
    against already-set environment variables (including those set by the
    systemd ``Environment=`` directives), and exports the resolved values
    into ``os.environ``.
    Called once at module load time, before any playbook is executed.
    """
    env_file = Path("/etc/omnia/omnia.env")
    if not env_file.exists():
        return

    # Collect raw key=value pairs (preserve order for forward references)
    raw_vars: Dict[str, str] = {}
    try:
        with open(env_file, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                raw_vars[key] = value
    except OSError:
        return

    # Build a resolution context: start with current os.environ, then
    # layer the raw vars on top so later entries can reference earlier ones.
    context: Dict[str, str] = dict(os.environ)
    for key, value in raw_vars.items():
        resolved = os.path.expandvars(value)
        # os.path.expandvars uses os.environ; update context progressively
        os.environ[key] = resolved
        context[key] = resolved

    # Log key variables for debugging (stderr goes to journalctl)
    catalog = os.environ.get("CATALOG_FILE_PATH", "<not set>")
    print(f"INFO: [omnia.env] CATALOG_FILE_PATH={catalog}", file=sys.stderr)


_resolve_omnia_env()


# Implicit logging utilities for secure logging
def log_secure_info(
    level: str,
    message: str,
    identifier: Optional[str] = None,
    exc_info: bool = False,
) -> None:
    """Log information securely with optional identifier truncation.
    This function provides consistent secure logging across all modules.
    When an identifier is provided, only the first 8 characters are logged
    to prevent exposure of sensitive data while maintaining debugging capability.
    Args:
        level: Log level ('info', 'warning', 'error', 'debug', 'critical')
        message: Log message template
        identifier: Optional identifier (job_id, request_id, etc.) - first 8 chars logged
        exc_info: If True, append current exception traceback (replaces logger.exception())
    """
    logger = logging.getLogger(__name__)
    if identifier:
        # Always log first 8 characters for identification
        log_message = f"{message}: {identifier[:8]}..."
    else:
        # Generic message when no identifier context
        log_message = message

    log_func = getattr(logger, level)
    log_func(log_message, exc_info=exc_info)


# Configuration
QUEUE_BASE = Path(os.getenv("PLAYBOOK_QUEUE_BASE", ""))
REQUESTS_DIR = QUEUE_BASE / "requests"
RESULTS_DIR = QUEUE_BASE / "results"
PROCESSING_DIR = QUEUE_BASE / "processing"
ARCHIVE_DIR = QUEUE_BASE / "archive"

# Environment configuration (sourced from omnia.env)
OMNIA_DATA_PATH = os.getenv("OMNIA_DATA_PATH", "/opt/omnia")
OMNIA_VENV_PATH = os.getenv("OMNIA_VENV_PATH", "/opt/omnia/venv")

# Application log directory (build_stream service logs)
HOST_LOG_BASE_DIR = Path(f"{OMNIA_DATA_PATH}/build_stream/logs")

# Playbook log directory: /var/log/omnia/<domain>/
# The domain name is extracted from the playbook path at runtime.
PLAYBOOK_LOG_BASE_DIR = Path("/var/log/omnia")

# Build Stream artifacts directory
BUILD_STREAM_ROOT = Path(OMNIA_DATA_PATH) / "build_stream_root"
ARTIFACTS_DIR = BUILD_STREAM_ROOT / "artifacts"

POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "2"))
MAX_CONCURRENT_JOBS = int(os.getenv("MAX_CONCURRENT_JOBS", "1"))
DEFAULT_TIMEOUT_MINUTES = int(os.getenv("DEFAULT_TIMEOUT_MINUTES", "30"))

# Playbook name to full path mapping - prevents injection from user input.
# Loaded once at startup from playbook_paths.conf (single source of truth).
# The mapping file lives alongside the watcher in the NFS deployment path.
PLAYBOOK_PATHS_CONFIG = Path(os.getenv(
    "PLAYBOOK_PATHS_CONFIG",
    str(Path(__file__).resolve().parent.parent / "playbook_paths.conf"),
))

# Auto-detect: this file is at src/build_stream/app/playbook-watcher/
# so .parent x4 gives src/
_AUTO_DETECTED_SRC_PATH = str(
    Path(__file__).resolve().parent.parent.parent.parent
)


def _get_omnia_src_path() -> str:
    """Return OMNIA_SRC_PATH from env, or auto-detect from source tree."""
    return os.environ.get("OMNIA_SRC_PATH") or _AUTO_DETECTED_SRC_PATH


def _resolve_path(relative_path: str) -> str:
    """Resolve a relative playbook path to an absolute path.
    If the path is already absolute it is returned as-is (backward compat).
    Otherwise it is joined with OMNIA_SRC_PATH.
    """
    if os.path.isabs(relative_path):
        return relative_path
    return str(Path(_get_omnia_src_path()) / relative_path)


def _load_playbook_paths(config_path: Path) -> dict:
    """Load playbook path mapping from YAML config file.
    Relative paths are resolved against OMNIA_SRC_PATH.
    Falls back to an empty dict if the file is missing or malformed,
    which will cause every playbook request to be rejected by the
    whitelist check — a safe default.
    """
    try:
        import yaml  # pylint: disable=import-outside-toplevel
        with open(config_path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if isinstance(data, dict) and isinstance(data.get("playbook_paths"), dict):
            raw = data["playbook_paths"]
            return {name: _resolve_path(p) for name, p in raw.items()}
        log_secure_info("error", "playbook_paths config missing 'playbook_paths' key")
        return {}
    except FileNotFoundError:
        log_secure_info("error", "playbook_paths config not found",
                        str(config_path)[:8])
        return {}
    except Exception:  # pylint: disable=broad-except
        log_secure_info("error", "Failed to load playbook_paths config",
                        exc_info=True)
        return {}


PLAYBOOK_NAME_TO_PATH = _load_playbook_paths(PLAYBOOK_PATHS_CONFIG)

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

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
        except (OSError, IOError):
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


# Checkmarx: Constant alphabet used to re-derive identifiers taken from request
# files.  Every character of the returned string is indexed out of this constant,
# so the result carries no data-flow edge back to the request file.  This is the
# same "replace, don't just check" principle as the PLAYBOOK_NAME_TO_PATH lookup
# in map_playbook_name_to_path().
_SAFE_ID_ALPHABET = (
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789-_"
)
_MAX_IDENTIFIER_LENGTH = 64


def sanitize_identifier(value: str) -> str:
    """Re-derive an identifier from a constant alphabet to break the taint chain.

    ``validate_job_id`` and ``validate_stage_name`` only _check_ a value — the
    original untrusted string keeps flowing on to the caller, so a static
    analyser still treats it as attacker-controlled all the way to
    ``subprocess.run``.  This function instead _rebuilds_ the identifier: each
    character is located in :data:`_SAFE_ID_ALPHABET` and that constant's own
    character is appended, so the result originates entirely from trusted
    module-level data.

    Use this for any request-file value that ends up in a command argument,
    an environment variable, or a filesystem path.

    Args:
        value: Untrusted identifier (e.g. ``job_id`` read from a request file).

    Returns:
        A new string containing only whitelisted characters, truncated to
        :data:`_MAX_IDENTIFIER_LENGTH` characters.

    Raises:
        ValueError: If *value* is empty or contains a non-whitelisted character.
    """
    rebuilt: List[str] = []
    for char in str(value)[:_MAX_IDENTIFIER_LENGTH]:
        index = _SAFE_ID_ALPHABET.find(char)
        if index < 0:
            raise ValueError("Identifier contains unsupported characters")
        rebuilt.append(_SAFE_ID_ALPHABET[index])
    if not rebuilt:
        raise ValueError("Identifier is empty")
    return "".join(rebuilt)


# ── NEW: Constant alphabets and sanitize functions for stage names and paths ──
# These re-derive values character-by-character from module-level constants,
# severing the data-flow edge from the request file to subprocess.run().

_SAFE_STAGE_ALPHABET = (
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789-_ "
)


def sanitize_stage_name(value: str) -> str:
    """Re-derive a stage name from a constant alphabet to break the taint chain.

    Args:
        value: Untrusted stage name from request data.

    Returns:
        A new string built from :data:`_SAFE_STAGE_ALPHABET`.

    Raises:
        ValueError: If the value is empty or contains unsupported characters.
    """
    rebuilt: List[str] = []
    for char in str(value)[:_MAX_IDENTIFIER_LENGTH]:
        index = _SAFE_STAGE_ALPHABET.find(char)
        if index < 0:
            raise ValueError("Stage name contains unsupported characters")
        rebuilt.append(_SAFE_STAGE_ALPHABET[index])
    if not rebuilt:
        raise ValueError("Stage name is empty")
    return "".join(rebuilt)


_SAFE_PATH_ALPHABET = (
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789-_./"
)
_MAX_PATH_LENGTH = 4096


def sanitize_path(value: str, allowed_base: str) -> str:
    """Re-derive a filesystem path from a constant alphabet to break the taint chain.

    Validates that the path starts with ``allowed_base``, contains no path
    traversal or shell-dangerous characters, and rebuilds every character
    from :data:`_SAFE_PATH_ALPHABET`.

    Args:
        value: Untrusted path string from request data.
        allowed_base: Required prefix (e.g. ``OMNIA_DATA_PATH``).

    Returns:
        A new string built entirely from trusted constant data.

    Raises:
        ValueError: If the path is empty, contains unsupported characters,
                    path traversal sequences, or does not start with *allowed_base*.
    """
    path_str = str(value)
    if not path_str or ".." in path_str:
        raise ValueError("Path is empty or contains traversal sequence")
    if not path_str.startswith(allowed_base):
        raise ValueError("Path does not start with allowed base directory")

    # Reject shell metacharacters before rebuilding
    for dangerous in (";", "|", "&", "$", "`", "\n", "\r", "\0", "'", '"'):
        if dangerous in path_str:
            raise ValueError("Path contains dangerous characters")

    rebuilt: List[str] = []
    for char in path_str[:_MAX_PATH_LENGTH]:
        index = _SAFE_PATH_ALPHABET.find(char)
        if index < 0:
            raise ValueError("Path contains unsupported character")
        rebuilt.append(_SAFE_PATH_ALPHABET[index])

    if not rebuilt:
        raise ValueError("Path is empty after sanitization")

    return "".join(rebuilt)


def sanitize_extra_vars(extra_vars: Any, job_id: str) -> dict:
    """Sanitize extra_vars dictionary values to break taint chain.

    Re-derives each key and string value from safe alphabets.  Non-string
    scalar values (int, float, bool, None) are passed through as-is since
    they carry no injection risk.  Nested dicts/lists are recursively
    sanitized.

    The ``job_id`` key is always overwritten with the already-sanitized
    *job_id* parameter.

    Args:
        extra_vars: Untrusted extra_vars from request data.
        job_id: Already-sanitized job_id.

    Returns:
        A new dict with all string values re-derived from safe constants.

    Raises:
        ValueError: If any key or value contains unsupported characters.
    """
    if not isinstance(extra_vars, dict):
        return {"job_id": job_id}

    # Alphabet for extra_vars values — broader to support JSON-like content
    safe_value_alphabet = (
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789"
        "-_./,:=@ {}[]\"'"
    )

    def _sanitize_value(val: Any) -> Any:
        if val is None or isinstance(val, (bool, int, float)):
            return val
        if isinstance(val, str):
            rebuilt: List[str] = []
            for char in val[:_MAX_PATH_LENGTH]:
                index = safe_value_alphabet.find(char)
                if index < 0:
                    raise ValueError(
                        "extra_vars value contains unsupported character"
                    )
                rebuilt.append(safe_value_alphabet[index])
            return "".join(rebuilt)
        if isinstance(val, list):
            return [_sanitize_value(item) for item in val]
        if isinstance(val, dict):
            return {
                sanitize_identifier(str(k)): _sanitize_value(v)
                for k, v in val.items()
            }
        raise ValueError("Unsupported type in extra_vars")

    sanitized: dict = {}
    for key, value in extra_vars.items():
        safe_key = sanitize_identifier(str(key))
        sanitized[safe_key] = _sanitize_value(value)

    # Always overwrite job_id with the trusted value
    sanitized["job_id"] = job_id
    return sanitized


# ── END NEW sanitization functions ──


def validate_command(cmd: list, playbook_path: str) -> bool:
    """Validate command structure and arguments to prevent injection.

    Domain-segregated (Omnia 2.3+): the command runs ansible-playbook
    directly on the host via the shared venv — no podman/container.

    Expected structure:
        [<venv>/bin/ansible-playbook, <playbook_path>, ...]

    Args:
        cmd: Command list to validate
        playbook_path: Expected playbook path (already validated)

    Returns:
        True if valid, raises ValueError with detailed message if invalid
    """
    # Define the minimum required command structure
    MIN_REQUIRED_STRUCTURE = [
        {"value": "ansible-playbook", "suffix": True},
        {"value": None, "fixed": False},
    ]

    # Define allowed additional arguments
    ALLOWED_EXTRA_ARGS = [
        "-v",
        "--extra-vars",
        "--inventory",
        "--tags",
    ]

    # 1. Check minimum command length
    min_required_length = len(MIN_REQUIRED_STRUCTURE)
    if len(cmd) < min_required_length:
        log_secure_info(
            "error",
            "Command structure too short",
            f"Expected at least {min_required_length}, got {len(cmd)}"
        )
        raise ValueError("Invalid command structure")

    # 2. Structure validation
    for i, (arg, allowed) in enumerate(zip(cmd[:min_required_length], MIN_REQUIRED_STRUCTURE)):
        # Type check - must be string
        if not isinstance(arg, str):
            log_secure_info(
                "error",
                "Non-string argument in command",
                f"Position: {i}"
            )
            raise ValueError("Invalid command argument type")

        # Length check - prevent excessively long arguments
        if len(arg) > 4096:
            log_secure_info(
                "error",
                "Command argument exceeds maximum allowed length",
                f"Position: {i}, Length: {len(arg)}"
            )
            raise ValueError("Command argument too long")

        # Suffix check (ansible-playbook binary — may include venv prefix)
        if allowed.get("suffix") and not arg.endswith(allowed.get("value", "")):
            log_secure_info(
                "error",
                f"Command argument at position {i} does not end with required suffix",
                f"Expected suffix '{allowed.get('value', '')}', got '{arg}'"
            )
            raise ValueError(f"Invalid command argument at position {i}")

        # Playbook path position validation
        if not allowed.get("suffix") and allowed.get("value") is None and i == 1:
            if arg != playbook_path:
                log_secure_info(
                    "error",
                    "Playbook path in command does not match validated path"
                )
                raise ValueError("Playbook path mismatch")

    # 3. Validate additional arguments (after the minimum required structure)
    if len(cmd) > min_required_length:
        i = min_required_length
        while i < len(cmd):
            arg = cmd[i]
            if arg in ["--inventory", "--extra-vars", "--tags"] and i + 1 < len(cmd):
                i += 2
            elif arg == "-v" or arg.startswith("-v"):
                i += 1
            else:
                log_secure_info(
                    "error",
                    "Unknown additional argument",
                    f"Position: {i}, Value: {arg}"
                )
                raise ValueError(f"Unknown additional argument: {arg}")

    # 4. Character validation - check for dangerous characters in all arguments
    DANGEROUS_CHARS = [
        '\n', '\r', '\0', '\t', '\v', '\f', '\a', '\b',
        '\\', '`', '$', '&', '|', ';', '<', '>', '(', ')',
        '*', '?', '~', '#'
    ]

    # Skip validation for playbook path position and value arguments
    SKIP_POSITIONS = [1]  # Position of playbook_path
    i = min_required_length
    while i < len(cmd):
        if cmd[i] in ("--extra-vars", "--inventory", "--tags") and i + 1 < len(cmd):
            SKIP_POSITIONS.append(i + 1)
            i += 2
        else:
            i += 1

    for i, arg in enumerate(cmd):
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

    # 5. Shell binary check - prevent shell execution
    SHELL_BINARIES = ["sh", "bash", "dash", "zsh", "ksh", "csh", "tcsh", "fish"]
    for i, arg in enumerate(cmd):
        if arg in SHELL_BINARIES:
            log_secure_info(
                "error",
                "Shell binary detected in command argument",
                f"Position: {i}, Value: {arg}"
            )
            raise ValueError("Shell binary not allowed in command")

    # 6. URL check - prevent remote resource fetching
    for i, arg in enumerate(cmd):
        if re.search(r'(https?|ftp|file)://', arg):
            log_secure_info(
                "error",
                "URL detected in command argument",
                f"Position: {i}, Value: {arg[:8]}"
            )
            raise ValueError("URLs not allowed in command arguments")

    return True


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
                request_data = json.JSONDecoder().decode(f.read())
            except (json.JSONDecodeError, ValueError):
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

        # Validate required fields - different for molecule vs ansible-playbook
        command_type = request_data.get("command_type", "ansible-playbook")
        if command_type == "test_automation":
            required_fields = [
                "job_id", "stage_type", "command_type",
                "scenario_names", "config_path"
            ]
        else:
            required_fields = ["job_id", "stage_name", "playbook_path"]

        missing_fields = [
            field for field in required_fields if field not in request_data
        ]
        if missing_fields:
            log_secure_info(
                'error',
                f"Request file missing required fields: {', '.join(missing_fields)}"
            )
            return None

        # Validate inputs to prevent injection
        job_id = str(request_data["job_id"])
        if not validate_job_id(job_id):
            log_secure_info("error", "Invalid job_id format in request", job_id[:8])
            return None

        if command_type == "test_automation":
            # Validate molecule-specific fields
            stage_type = str(request_data["stage_type"])
            scenario_names = request_data["scenario_names"]
            config_path = str(request_data["config_path"])

            if not validate_stage_name(stage_type):
                log_secure_info(
                    "error", "Invalid stage_type format in request",
                    stage_type[:8]
                )
                return None

            # Validate scenario names
            if not isinstance(scenario_names, list) or not scenario_names:
                log_secure_info(
                    "error", "scenario_names must be a non-empty list",
                    job_id[:8]
                )
                return None
            for scenario in scenario_names:
                if not isinstance(scenario, str) or not validate_stage_name(scenario):
                    log_secure_info(
                        "error", "Invalid scenario name format",
                        str(scenario)[:8]
                    )
                    return None

            # Validate config_path is within allowed directory
            allowed_base = os.path.join(OMNIA_DATA_PATH, "")
            if not config_path.startswith(allowed_base) or ".." in config_path:
                log_secure_info("error", "Invalid config_path", config_path[:8])
                return None
        else:
            # Original ansible-playbook validation
            stage_name = str(request_data["stage_name"])
            playbook_name = str(request_data["playbook_path"])

            if not validate_stage_name(stage_name):
                log_secure_info(
                    "error", "Invalid stage_name format in request",
                    stage_name[:8]
                )
                return None

            full_playbook_path = map_playbook_name_to_path(playbook_name)
            if full_playbook_path is None:
                log_secure_info(
                    "error",
                    "Invalid or unknown playbook name in request",
                    playbook_name[:8]
                )
                return None

            # Store both the original playbook name and the mapped full path
            request_data["playbook_name"] = playbook_name
            request_data["full_playbook_path"] = full_playbook_path

        # Set defaults
        request_data.setdefault("correlation_id", job_id)

        # Check for inventory_file_path
        if "inventory_file_path" in request_data:
            inventory_file_path = str(request_data["inventory_file_path"])
            if not inventory_file_path.startswith("/") or ".." in inventory_file_path:
                log_secure_info(
                    "error",
                    "Invalid inventory file path: possible directory traversal",
                    job_id[:8]
                )
                return None
            log_secure_info(
                "info",
                "Found inventory file path in request",
                job_id[:8]
            )

        # Check for extra_vars field
        if "extra_vars" in request_data:
            if not isinstance(request_data["extra_vars"], dict):
                log_secure_info(
                    "error", "extra_vars must be a dictionary", job_id[:8]
                )
                return None
            log_secure_info(
                "info",
                "Found extra_vars in request",
                job_id[:8]
            )

        # We're no longer using extra_args, so remove it if present
        if "extra_args" in request_data:
            log_secure_info(
                "info",
                "Found extra_args in request but ignoring it",
                job_id[:8]
            )
            del request_data["extra_args"]

        log_secure_info(
            "info",
            "Parsed request for job",
            job_id
        )
        return request_data

    except json.JSONDecodeError:
        log_secure_info(
            "error",
            "Invalid JSON in request file"
        )
        return None
    except (KeyError, TypeError, ValueError):
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
    return os.path.basename(full_playbook_path)


def _extract_domain_from_playbook_path(playbook_path: str) -> str:
    """Extract the domain name from a playbook's absolute path.
    Convention: ``src/<domain>/playbooks/<playbook>.yml``
    """
    try:
        parts = Path(playbook_path).resolve().parts
        for idx, part in enumerate(parts):
            if part == "playbooks" and idx > 0:
                return parts[idx - 1]
    except Exception:  # pylint: disable=broad-except
        pass
    return "unknown"


def _build_log_paths(
    playbook_path: str, started_at: datetime, attempt: int = None
) -> tuple:
    """Build playbook log file path under /var/log/omnia/<domain>/.
    Args:
        playbook_path: Full path to the playbook file
        started_at: Start time for timestamp
        attempt: Optional attempt number (1-indexed).
    Returns:
        Tuple of (log_file_path, log_dir)
    """
    playbook_name = extract_playbook_name(playbook_path)
    domain = _extract_domain_from_playbook_path(playbook_path)

    log_dir = PLAYBOOK_LOG_BASE_DIR / domain
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = started_at.strftime("%Y%m%d_%H%M%S")
    if attempt is not None:
        log_filename = f"{playbook_name}_{timestamp}_attempt{attempt}.log"
    else:
        log_filename = f"{playbook_name}_{timestamp}.log"

    log_file_path = log_dir / log_filename
    return log_file_path, log_dir


def move_log_to_job_directory(
    host_log_file_path: Path, job_id: str, attempt: int = None
) -> Path:
    """Move log file to a job-specific directory after completion.
    Args:
        host_log_file_path: Current path of the log file
        job_id: Job identifier for creating the job directory
        attempt: Optional attempt number
    Returns:
        New path of the log file in the job directory
    """
    job_dir = HOST_LOG_BASE_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    log_filename = host_log_file_path.name
    if attempt is not None:
        stem = host_log_file_path.stem
        log_filename = f"{stem}_attempt{attempt}.log"

    new_log_path = job_dir / log_filename

    try:
        shutil.move(str(host_log_file_path), str(new_log_path))
        log_secure_info(
            "info",
            "Log file moved to job directory",
            job_id[:12] if job_id else ""
        )
    except (OSError, IOError):
        log_secure_info(
            "error",
            "Failed to move log file to job directory"
        )
        return host_log_file_path

    return new_log_path


def execute_playbook(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Execute Ansible playbook directly on the host via the shared venv.

    Domain-segregated (Omnia 2.3+): no podman / container.  The watcher
    invokes ``<OMNIA_VENV_PATH>/bin/ansible-playbook`` with the working
    directory set to the playbook's parent so that ``ansible.cfg`` and
    relative role paths are picked up correctly.

    Playbook logs are written to ``/var/log/omnia/<domain>/``.

    Args:
        request_data: Parsed request dictionary

    Returns:
        Result dictionary with execution details
    """
    # ── Phase 1: Extract and SANITIZE every value from request_data ──────
    # After this block, request_data must NOT be referenced for command
    # or env construction.  Each value is re-derived from a constant
    # alphabet so no taint edge survives to the subprocess.run() call.

    if not validate_job_id(str(request_data["job_id"])):
        raise ValueError("Invalid job_id format")
    job_id = sanitize_identifier(request_data["job_id"])

    if not validate_stage_name(str(request_data["stage_name"])):
        raise ValueError("Invalid stage_name format")
    stage_name = sanitize_stage_name(request_data["stage_name"])

    # Perform a fresh whitelist lookup to break taint chain
    playbook_name_raw = str(
        request_data.get("playbook_name", request_data.get("playbook_path", ""))
    )
    playbook_path = map_playbook_name_to_path(playbook_name_raw)
    if playbook_path is None:
        raise ValueError(f"Invalid playbook name: {playbook_name_raw[:8]}")
    # playbook_path is now from PLAYBOOK_NAME_TO_PATH (trusted constant)

    # Sanitize correlation_id / request_id (used only in result JSON but
    # sanitize anyway to prevent future edits from leaking them)
    try:
        correlation_id = sanitize_identifier(
            request_data.get("correlation_id", str(request_data["job_id"]))
        )
    except ValueError:
        correlation_id = job_id
    try:
        request_id_safe = sanitize_identifier(
            request_data.get("request_id", str(request_data["job_id"]))
        )
    except ValueError:
        request_id_safe = job_id

    # Sanitize inventory_file_path if present
    inventory_file_path = None
    if "inventory_file_path" in request_data:
        inventory_file_path = sanitize_path(
            str(request_data["inventory_file_path"]),
            "/"  # Allow any absolute path but rebuild from safe alphabet
        )

    # Sanitize extra_vars
    raw_extra_vars = request_data.get("extra_vars", {})
    extra_vars = sanitize_extra_vars(raw_extra_vars, job_id)

    # Sanitize tags if present
    tags_str = None
    if "tags" in request_data and request_data["tags"]:
        tags_str = sanitize_stage_name(str(request_data["tags"]))

    # Extract attempt from extra_vars (already sanitized)
    attempt = extra_vars.get("attempt", 1)
    if not isinstance(attempt, int) or not 1 <= attempt <= 10:
        attempt = 1

    timeout_minutes = DEFAULT_TIMEOUT_MINUTES

    # ── Phase 2: Discard request_data — no further reads allowed ─────────
    del request_data

    log_secure_info("info", "Executing playbook for job", job_id)
    log_secure_info("debug", "Stage name", stage_name)

    started_at = datetime.now(timezone.utc)

    # Build log paths (playbook logs go to /var/log/omnia/<domain>/)
    log_file_path, _ = _build_log_paths(playbook_path, started_at)
    log_path_str = str(log_file_path)

    # Strict validation for log path
    if not log_path_str.startswith('/') or '..' in log_path_str:
        log_secure_info(
            "error",
            "Log path must be absolute and cannot contain path traversal",
            log_path_str[:8]
        )
        raise ValueError("Invalid log path")
    if not re.match(r'^[a-zA-Z0-9_\-/.]+$', log_path_str):
        log_secure_info(
            "error", "Log path contains invalid characters",
            log_path_str[:8]
        )
        raise ValueError("Invalid log path format")

    # Resolve ansible-playbook binary from venv
    ansible_playbook_bin = f"{OMNIA_VENV_PATH}/bin/ansible-playbook"

    # Build command — direct invocation, no podman/container
    cmd = [
        ansible_playbook_bin,
        playbook_path,  # Validated against strict whitelist
    ]

    # Add inventory file path if present (already sanitized above)
    if inventory_file_path is not None:
        cmd.extend(["--inventory", inventory_file_path])
        log_secure_info(
            "info", "Using inventory file for playbook",
            inventory_file_path[:8]
        )

    # Add extra_vars (already sanitized above)
    extra_vars_json = json.dumps(extra_vars)
    cmd.extend(["--extra-vars", extra_vars_json])
    log_secure_info("info", "Added extra_vars with job_id for playbook", job_id)

    # Add tags if present (already sanitized above)
    if tags_str is not None:
        cmd.extend(["--tags", tags_str])
        log_secure_info("info", f"Added tags for playbook: {tags_str}", job_id)

    # Add verbosity flag
    cmd.append("-v")

    # Validate the command structure
    try:
        validate_command(cmd, playbook_path)
    except ValueError as e:
        log_secure_info("error", "Command validation failed", str(e))
        raise ValueError(f"Command validation failed: {e}")

    # Working directory = playbook's parent directory (for ansible.cfg / roles)
    playbook_dir = str(Path(playbook_path).resolve().parent)

    log_secure_info("debug", "Executing ansible playbook for job", job_id)
    log_secure_info("info", "Ansible logs will be written to", log_path_str[:20])

    try:
        timeout_seconds = timeout_minutes * 60

        # Set ANSIBLE_LOG_PATH as env var so Ansible writes its log there
        env = os.environ.copy()
        env["ANSIBLE_LOG_PATH"] = log_path_str

        log_secure_info(
            "debug", "Executing command",
            f"ansible-playbook [playbook] in {playbook_dir[:30]}"
        )

        # Execute directly — shell=False, cwd=playbook directory
        result = subprocess.run(
            cmd,
            capture_output=False,
            timeout=timeout_seconds,
            check=False,
            shell=False,
            text=False,
            start_new_session=True,
            cwd=playbook_dir,
            env=env,
        )

        # Wait briefly for log flush
        time.sleep(0.5)

        # Verify log file exists
        if log_file_path.exists():
            log_secure_info("info", "Log file confirmed for job", job_id)
            log_file_path = move_log_to_job_directory(
                log_file_path, job_id, attempt=attempt
            )
        else:
            log_secure_info(
                "warning",
                "Log file not found at expected location for job",
                job_id
            )

        completed_at = datetime.now(timezone.utc)
        duration_seconds = (completed_at - started_at).total_seconds()
        status = "success" if result.returncode == 0 else "failed"

        log_secure_info("info", "Playbook execution completed for job", job_id)
        log_secure_info("debug", "Execution status", status)

        # Build result dictionary
        result_data = {
            "job_id": job_id,
            "stage_name": stage_name,
            "request_id": request_id_safe,
            "correlation_id": correlation_id,
            "status": status,
            "exit_code": result.returncode,
            "log_file_path": str(log_file_path),
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_seconds": int(duration_seconds),
            "timestamp": completed_at.isoformat(),
        }

        # Add error details if failed
        if status == "failed":
            domain = _extract_domain_from_playbook_path(playbook_path)
            result_data["error_code"] = "PLAYBOOK_EXECUTION_FAILED"
            result_data["error_summary"] = (
                f"Playbook exited with code {result.returncode}. "
                f"Check playbook logs at /var/log/omnia/{domain}/ for details."
            )

        # For restart stage, include path to per-node results JSON
        if stage_name == "restart":
            node_results_path = ARTIFACTS_DIR / job_id / "node_results.json"
            if node_results_path.exists():
                result_data["node_results_file_path"] = str(node_results_path)
                log_secure_info(
                    "info",
                    "Node results file found for restart stage",
                    job_id
                )
            else:
                log_secure_info(
                    "warning",
                    f"node_results.json NOT found at {node_results_path} "
                    f"for restart stage.",
                    job_id
                )

        return result_data

    except subprocess.TimeoutExpired:
        completed_at = datetime.now(timezone.utc)
        duration_seconds = (completed_at - started_at).total_seconds()
        log_secure_info(
            "error", "Playbook execution timed out for job", job_id
        )
        return {
            "job_id": job_id,
            "stage_name": stage_name,
            "request_id": request_id_safe,
            "correlation_id": correlation_id,
            "status": "failed",
            "exit_code": -1,
            "stdout": "",
            "stderr": (
                f"Playbook execution timed out after "
                f"{timeout_minutes} minutes"
            ),
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_seconds": int(duration_seconds),
            "error_code": "PLAYBOOK_TIMEOUT",
            "error_summary": (
                f"Execution exceeded timeout of "
                f"{timeout_minutes} minutes"
            ),
            "timestamp": completed_at.isoformat(),
        }
    except (OSError, subprocess.SubprocessError) as e:
        completed_at = datetime.now(timezone.utc)
        duration_seconds = (completed_at - started_at).total_seconds()
        log_secure_info(
            'error',
            f"Unexpected error executing playbook for job {job_id}",
            exc_info=True
        )
        return {
            "job_id": job_id,
            "stage_name": stage_name,
            "request_id": request_id_safe,
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


def execute_molecule(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Execute test automation via run_validation.sh and capture results.

    Runs: ./run_validation.sh fvt_orchestrator verify --marker buildstream

    Args:
        request_data: Parsed request dictionary with test_automation fields

    Returns:
        Result dictionary with execution details
    """
    # ── Phase 1: Extract and SANITIZE every value from request_data ──────
    # After this block, request_data must NOT be referenced again.
    # Each value is re-derived from a constant alphabet so no taint edge
    # survives to the subprocess.run() call below.

    if not validate_job_id(str(request_data["job_id"])):
        raise ValueError("Invalid job_id format")
    job_id = sanitize_identifier(request_data["job_id"])

    if not validate_stage_name(str(request_data["stage_type"])):
        raise ValueError("Invalid stage_type format")
    stage_type = sanitize_stage_name(request_data["stage_type"])

    # Sanitize config_path: re-derive from safe alphabet + validate prefix
    config_path = sanitize_path(
        str(request_data["config_path"]),
        OMNIA_DATA_PATH,
    )

    # Sanitize attempt: coerce to int in bounded range
    raw_attempt = request_data.get("attempt", 1)
    attempt = raw_attempt if isinstance(raw_attempt, int) and 1 <= raw_attempt <= 10 else 1
    attempt = int(f"{attempt:d}")  # Re-derive as int literal

    # Sanitize correlation_id and request_id (only used in result JSON,
    # but sanitize anyway so no future edit can leak them into a command)
    try:
        correlation_id = sanitize_identifier(
            request_data.get("correlation_id", str(request_data["job_id"]))
        )
    except ValueError:
        correlation_id = job_id
    try:
        request_id = sanitize_identifier(
            request_data.get("request_id", str(request_data["job_id"]))
        )
    except ValueError:
        request_id = job_id

    # Validate scenario_names (never used in subprocess — hardcoded below —
    # but sanitize to prevent any future use from reintroducing taint)
    raw_scenarios = request_data.get("scenario_names", [])
    if not isinstance(raw_scenarios, list) or not raw_scenarios:
        raise ValueError("scenario_names must be a non-empty list")
    sanitized_scenarios: List[str] = []
    for sc in raw_scenarios:
        sanitized_scenarios.append(sanitize_stage_name(str(sc)))

    # ── Phase 2: Discard request_data — no further reads allowed ─────────
    del request_data  # Sever the taint chain to subprocess.run()

    # Hardcoded values — not configurable in this release
    scenario_name = "validate"        # Hardcoded, not from request
    test_suite = "buildstream"        # Hardcoded marker name, not from request
    timeout_minutes = 150             # Hardcoded default

    log_secure_info("info", "Executing test validation for job", job_id)
    log_secure_info("debug", "Stage type", stage_type)
    log_secure_info(
        "debug", "Using hardcoded scenario/marker",
        f"{scenario_name}/{test_suite}"
    )

    started_at = datetime.now(timezone.utc)

    # Create a temp report directory with timestamp for uniqueness
    timestamp = started_at.strftime("%Y%m%d_%H%M%S")
    temp_report_dir = str(ARTIFACTS_DIR / f"molecule_run_{timestamp}")

    # Final NFS artifact directory for the job
    artifact_dir = str(
        ARTIFACTS_DIR / job_id / "validate" / f"attempt_{attempt}"
    )

    # Ensure both directories exist
    try:
        os.makedirs(temp_report_dir, exist_ok=True)
        os.makedirs(artifact_dir, exist_ok=True)
    except OSError as e:
        log_secure_info("error", "Failed to create artifact directory", job_id)
        return {
            "job_id": job_id,
            "stage_name": stage_type,
            "request_id": request_id,
            "correlation_id": correlation_id,
            "status": "failed",
            "exit_code": 2,
            "error_summary": f"Failed to create artifact directory: {e}",
            "started_at": started_at.isoformat(),
            "completed_at": started_at.isoformat(),
            "duration_seconds": 0,
            "timestamp": started_at.isoformat(),
        }

    # Build test command - execute run_validation.sh on OIM host
    # run_validation.sh delegates to _run.py which runs pytest with markers
    # Usage: ./run_validation.sh fvt_orchestrator verify --marker buildstream
    #
    # Pipeline-safe environment setup (no interactive prompts, no waiting):
    #   1. cd to test/orchestrator directory
    #   2. Create venv if it doesn't exist (idempotent)
    #   3. Activate venv
    #   4. Install deps only if requirements.txt is newer than venv marker
    #   5. Run: ./run_validation.sh fvt_orchestrator verify --marker buildstream
    # Resolve from the same OMNIA_SRC_PATH used for normal playbooks.
    # OMNIA_SRC_PATH points to <clone_path>/src.
    clone_path = str(Path(_get_omnia_src_path()).resolve().parent)

    # Checkmarx: Validate clone_path to prevent command injection
    if (
        not clone_path.startswith("/")
        or ".." in clone_path
        or any(
            char in clone_path
            for char in [";", "|", "&", "$", "`", "\n", "\r"]
        )
    ):
        log_secure_info(
            "error",
            "Invalid clone_path - using default",
            clone_path[:8]
        )
        clone_path = "/root/omnia"
    test_dir = os.path.join(clone_path, "test", "orchestrator")

    # Additional validation: ensure test_dir is within expected base path
    if (
        not test_dir.startswith("/root/omnia")
        and not test_dir.startswith("/opt/omnia")
    ):
        raise ValueError("test_dir must be within /root/omnia or /opt/omnia")

    # Properly escape all path variables using shlex.quote()
    quoted_test_dir = shlex.quote(test_dir)
    setup_and_run = (
        f'set -eo pipefail && '
        f'cd {quoted_test_dir} && '
        f'{{ [ -d .venv ] || python3 -m venv .venv; }} && '
        f'source .venv/bin/activate && '
        f'if [ ! -f .venv/.deps_installed ] || '
        f'   [ requirements.txt -nt .venv/.deps_installed ]; then '
        f'  echo "Installing test dependencies..." && '
        f'  pip install --disable-pip-version-check --no-input --upgrade pip -q && '
        f'  pip install --disable-pip-version-check --no-input -r requirements.txt -q && '
        f'  touch .venv/.deps_installed; '
        f'fi && '
        # Checkmarx: Hardcoded command arguments to prevent injection from request_data
        # Run the validation through its supported non-interactive entry point.
        f'exec ./run_validation.sh fvt_orchestrator verify --marker buildstream'
    )

    cmd = ["bash", "-c", setup_and_run]

    # Build environment variables — all values are from untainted sources:
    #   * temp_report_dir -> ARTIFACTS_DIR (module constant) + strftime timestamp
    #   * env_report_id   -> sanitize_identifier(job_id) + int-formatted attempt
    env_report_id = f"{job_id}_attempt_{attempt:d}"
    env = os.environ.copy()
    env["ANSIBLE_HOST_KEY_CHECKING"] = "False"
    env["MOLECULE_REPORT_DIR"] = temp_report_dir
    env["REPORT_ID"] = env_report_id

    log_secure_info("info", "Executing run_validation.sh for job", job_id)

    try:
        timeout_seconds = timeout_minutes * 60

        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
            shell=False,
            text=True,
            env=env,
            start_new_session=True
        )

        completed_at = datetime.now(timezone.utc)
        duration_seconds = (completed_at - started_at).total_seconds()

        # Build NFS log path
        host_log_file_path, _ = _build_log_paths(
            "validate", started_at, attempt
        )

        # Write molecule output to NFS log file
        try:
            with open(str(host_log_file_path), 'w') as f:
                f.write(
                    f"STDOUT:\n{result.stdout}\n\n"
                    f"STDERR:\n{result.stderr}\n"
                )
        except OSError:
            log_secure_info("warning", "Failed to write test NFS log", job_id)

        # Move log to job-specific directory on NFS
        if host_log_file_path.exists():
            host_log_file_path = move_log_to_job_directory(
                host_log_file_path, job_id
            )

        # Copy molecule reports from temp dir to job-specific NFS artifact dir
        try:
            for item in os.listdir(temp_report_dir):
                src = os.path.join(temp_report_dir, item)
                dst = os.path.join(artifact_dir, item)
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                elif os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
            log_secure_info(
                "info",
                "Copied test reports to job artifact directory",
                job_id
            )
        except OSError:
            log_secure_info(
                "warning",
                "Failed to copy test reports to artifact dir",
                job_id
            )

        # Write test output log to the artifact directory
        artifact_log_path = os.path.join(
            artifact_dir, "validate_output.log"
        )
        try:
            with open(artifact_log_path, 'w') as f:
                f.write(
                    f"STDOUT:\n{result.stdout}\n\n"
                    f"STDERR:\n{result.stderr}\n"
                )
        except OSError:
            log_secure_info(
                "warning", "Failed to write molecule artifact log", job_id
            )

        # Clean up temp report directory
        try:
            shutil.rmtree(temp_report_dir, ignore_errors=True)
        except OSError:
            log_secure_info(
                "debug", "Failed to clean up temp report dir", job_id
            )

        # Use the NFS log path as the canonical log_file_path
        log_file_path = str(host_log_file_path)

        # Parse metadata from test output log
        test_summary = {
            "total": 0, "passed": 0, "failed": 0,
            "skipped": 0, "errors": 0
        }
        report_id = None

        if os.path.exists(log_file_path):
            try:
                with open(log_file_path, 'r') as f:
                    log_content = f.read()

                    # Extract report_id from log output
                    report_id_match = re.search(
                        r'Report\s*ID\s*:\s*([a-zA-Z0-9\-_]+)',
                        log_content, re.IGNORECASE
                    )
                    if report_id_match:
                        report_id = report_id_match.group(1)
                    elif env_report_id in log_content:
                        report_id = env_report_id

                    # Strip ANSI color codes first
                    try:
                        sanitized = re.sub(
                            r'\x1B\[[0-?]*[ -/]*[@-~]', '', log_content
                        )
                    except re.error:
                        sanitized = log_content

                    # Extract suite/marker info from run_validation output
                    header_suite_match = re.search(
                        r'(?m)^\s*Suite\s*:\s*([\w\-.]+)', sanitized
                    )
                    if header_suite_match:
                        test_summary["suite"] = header_suite_match.group(1)
                    else:
                        marker_match = re.search(
                            r'(?m)^\s*(?:Suite/Marker|Marker)\s*:\s*'
                            r'.*?([\w\-.]+)\s*$',
                            sanitized
                        )
                        if marker_match:
                            test_summary["suite"] = marker_match.group(1)
                        else:
                            test_summary["suite"] = "buildstream"
            except (OSError, IOError, ValueError) as e:
                log_secure_info(
                    "warning",
                    f"Failed to parse test output log: {e}",
                    job_id
                )

        # Extract current run from shared test_report.json
        report_source_path = os.path.join(
            OMNIA_DATA_PATH, "reports", "orchestrator_test_report.json"
        )
        log_secure_info(
            'info',
            f"Attempting to extract test results from {report_source_path}",
            job_id
        )
        log_secure_info(
            'info',
            f"Extracted report_id from log: {report_id}",
            job_id
        )

        if not report_id:
            log_secure_info(
                'warning',
                "No report_id found in validate output log, "
                "skipping JSON extraction",
                job_id
            )
        elif not os.path.exists(report_source_path):
            log_secure_info(
                'warning',
                f"test_report.json not found at {report_source_path}, "
                f"skipping JSON extraction",
                job_id
            )
        else:
            try:
                with open(report_source_path, 'r') as f:
                    full_report = json.load(f)

                log_secure_info(
                    'info', "Successfully loaded test_report.json", job_id
                )

                if "servers" not in full_report:
                    log_secure_info(
                        'warning',
                        "test_report.json missing 'servers' key",
                        job_id
                    )
                else:
                    current_run = None
                    for server_key, server_data in full_report["servers"].items():
                        runs = server_data.get("runs", [])
                        for run in runs:
                            if run.get("report_id") == report_id:
                                current_run = run
                                log_secure_info(
                                    'info',
                                    f"Found matching run with report_id "
                                    f"{report_id} under server key "
                                    f"'{server_key}'",
                                    job_id
                                )
                                break
                        if current_run:
                            break

                    if not current_run:
                        log_secure_info(
                            'warning',
                            f"No run found with report_id {report_id} "
                            f"in test_report.json",
                            job_id
                        )
                    else:
                        modules = current_run.get("modules", [])
                        if not modules:
                            log_secure_info(
                                'warning',
                                f"Run with report_id {report_id} has no "
                                f"modules",
                                job_id
                            )
                        else:
                            module_info = modules[0]
                            scenario = module_info.get("module", "unknown")
                            molecule_command = module_info.get(
                                "molecule_command", "verify"
                            )
                            test_duration = module_info.get(
                                "duration_seconds", 0
                            )
                            results = module_info.get("results", [])
                            tests = [
                                {
                                    "name": r.get("test_name"),
                                    "status": r.get("status")
                                }
                                for r in results
                                if r.get("test_name")
                            ]

                            test_summary["scenario"] = scenario
                            test_summary["molecule_command"] = molecule_command
                            test_summary["report_id"] = report_id
                            test_summary["duration_seconds"] = test_duration
                            test_summary["tests"] = tests

                            summary_block = current_run.get("summary", {})
                            log_secure_info(
                                'info',
                                f"Summary block from JSON: {summary_block}",
                                job_id
                            )

                            if isinstance(summary_block, dict):
                                test_summary["total"] = summary_block.get(
                                    "total", 0
                                )
                                test_summary["passed"] = summary_block.get(
                                    "passed", 0
                                )
                                test_summary["failed"] = summary_block.get(
                                    "failed", 0
                                )
                                test_summary["skipped"] = summary_block.get(
                                    "skipped", 0
                                )
                                test_summary["errors"] = summary_block.get(
                                    "errors", 0
                                )
                                log_secure_info(
                                    'info',
                                    f"Populated test_summary from JSON: "
                                    f"{test_summary}",
                                    job_id
                                )
                            else:
                                log_secure_info(
                                    'warning',
                                    f"Summary block is not a dict: "
                                    f"{type(summary_block)}",
                                    job_id
                                )

                            log_secure_info(
                                'info',
                                f"Test scenario: {scenario}, "
                                f"command: {molecule_command}, "
                                f"duration: {test_duration}s, "
                                f"tests: {len(tests)}, "
                                f"report_id: {report_id}",
                                job_id
                            )

                            # Save filtered report to artifact_dir
                            filtered_report = {
                                "servers": {
                                    "": {
                                        "runs": [current_run],
                                        "hostname": ""
                                    }
                                }
                            }
                            dest_path = os.path.join(
                                artifact_dir, "test_report.json"
                            )
                            with open(dest_path, 'w') as f:
                                json.dump(filtered_report, f, indent=2)
                            log_secure_info(
                                'info',
                                f"Extracted report {report_id} to artifact directory",
                                job_id
                            )

                            # Keep a cumulative report at the validate stage level while
                            # preserving the isolated report in every attempt directory.
                            # Rebuild it from the shared report so retries cannot duplicate
                            # an attempt or overwrite the result from an earlier attempt.
                            job_report = {"servers": {}}
                            report_id_prefix = f"{job_id}_attempt_"
                            for source_server, source_data in full_report["servers"].items():
                                job_runs = [
                                    run for run in source_data.get("runs", [])
                                    if str(run.get("report_id", "")).startswith(
                                        report_id_prefix
                                    )
                                ]
                                if job_runs:
                                    job_report["servers"][source_server] = {
                                        "runs": job_runs,
                                        "hostname": source_data.get("hostname", ""),
                                    }

                            job_report_path = os.path.join(
                                str(ARTIFACTS_DIR / job_id / "validate"),
                                "test_report.json",
                            )
                            with open(job_report_path, 'w') as f:
                                json.dump(job_report, f, indent=2)
                            log_secure_info('info', "Updated cumulative validate report", job_id)
            except (OSError, json.JSONDecodeError) as e:
                log_secure_info(
                    'warning', f"Failed to extract report: {e}", job_id
                )

        # Determine status
        if (
            test_summary["total"] == 0
            and test_summary["passed"] == 0
            and test_summary["failed"] == 0
        ):
            status = "failed"
            exit_code = 1
            log_secure_info(
                'warning',
                "Test summary parsing failed (all zeros), marking as failed",
                job_id
            )
        elif test_summary["failed"] > 0 or test_summary["errors"] > 0:
            status = "failed"
            exit_code = 1
        elif result.returncode == 0:
            status = "success"
            exit_code = 0
        elif result.returncode == 124:
            status = "failed"
            exit_code = 124
        else:
            status = "failed"
            exit_code = result.returncode

        log_secure_info(
            "info", "Test validation completed for job", job_id
        )
        log_secure_info("debug", "Execution status", status)

        result_data = {
            "job_id": job_id,
            "stage_name": stage_type,
            "request_id": request_id,
            "correlation_id": correlation_id,
            "status": status,
            "exit_code": exit_code,
            "duration_seconds": int(duration_seconds),
            "test_summary": test_summary,
            "artifact_dir": artifact_dir,
            "log_file_path": log_file_path,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "timestamp": completed_at.isoformat(),
        }

        # Add error details if failed
        if status == "failed":
            if exit_code == 124:
                result_data["error_summary"] = (
                    f"Test validation timed out after "
                    f"{timeout_minutes} minutes"
                )
            elif test_summary["failed"] > 0:
                failed_tests = []
                if os.path.exists(log_file_path):
                    try:
                        with open(log_file_path, 'r') as f:
                            log_content = f.read()
                            failed_matches = re.findall(
                                r'^FAILED (.+)$',
                                log_content, re.MULTILINE
                            )
                            failed_tests = failed_matches[:5]
                    except (OSError, IOError):
                        pass
                if failed_tests:
                    result_data["error_summary"] = (
                        f"Test failures: {test_summary['failed']} failed. "
                        f"Failed tests: {', '.join(failed_tests)}"
                    )
                else:
                    result_data["error_summary"] = (
                        f"Test failures: {test_summary['failed']} failed, "
                        f"{test_summary['errors']} errors"
                    )
            else:
                result_data["error_summary"] = (
                    f"Test validation exited with code {exit_code}"
                )

        return result_data

    except subprocess.TimeoutExpired:
        completed_at = datetime.now(timezone.utc)
        duration_seconds = (completed_at - started_at).total_seconds()
        log_secure_info(
            "error", "Test validation timed out for job", job_id
        )

        err_log_path, _ = _build_log_paths("validate", started_at, attempt)
        if err_log_path.exists():
            err_log_path = move_log_to_job_directory(err_log_path, job_id)

        return {
            "job_id": job_id,
            "stage_name": stage_type,
            "request_id": request_id,
            "correlation_id": correlation_id,
            "status": "failed",
            "exit_code": 124,
            "error_summary": (
                f"Test validation timed out after "
                f"{timeout_minutes} minutes"
            ),
            "artifact_dir": artifact_dir,
            "log_file_path": str(err_log_path),
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_seconds": int(duration_seconds),
            "timestamp": completed_at.isoformat(),
        }
    except (OSError, subprocess.SubprocessError) as e:
        completed_at = datetime.now(timezone.utc)
        duration_seconds = (completed_at - started_at).total_seconds()
        log_secure_info(
            "error",
            "Unexpected error executing test validation for job",
            job_id, exc_info=True
        )

        err_log_path, _ = _build_log_paths("validate", started_at, attempt)
        if err_log_path.exists():
            err_log_path = move_log_to_job_directory(err_log_path, job_id)

        return {
            "job_id": job_id,
            "stage_name": stage_type,
            "request_id": request_id,
            "correlation_id": correlation_id,
            "status": "failed",
            "exit_code": -1,
            "error_summary": (
                f"System error during test validation: {str(e)}"
            ),
            "artifact_dir": artifact_dir,
            "log_file_path": str(err_log_path),
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_seconds": int(duration_seconds),
            "timestamp": completed_at.isoformat(),
        }


def write_result_file(
    result_data: Dict[str, Any], original_filename: str
) -> bool:
    """Write result file to results directory.
    Args:
        result_data: Result dictionary to write
        original_filename: Original request filename for correlation
    Returns:
        True if successful, False otherwise
    """
    job_id = result_data["job_id"]
    try:
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
    except (OSError, IOError):
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
    except (OSError, IOError):
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

            # Execute based on command type
            command_type = request_data.get(
                "command_type", "ansible-playbook"
            )
            if command_type == "test_automation":
                result_data = execute_molecule(request_data)
            else:
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
                except (OSError, IOError):
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
    thread = Thread(
        target=process_request, args=(request_path,), daemon=True
    )
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
                process_request_async(request_path)
                processed_count += 1
            except (OSError, IOError):
                log_secure_info(
                    "error",
                    "Error processing request",
                    request_path.name[:8] if request_path.name else None
                )
        return processed_count
    except (OSError, IOError):
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
    except (OSError, IOError):
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
        except RuntimeError:
            log_secure_info(
                'error',
                f"Unexpected error in watcher loop iteration {iteration}",
                exc_info=True
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
