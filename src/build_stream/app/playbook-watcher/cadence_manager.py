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

"""Cadence Manager for periodic catalog builds.

Implements the cadence polling loop that:
1. Periodically invokes repo_manager to sync packages for the cadence catalog
2. On successful sync, bumps the catalog version and pushes to GitLab via API
3. GitLab CI triggers the unified cadence pipeline (build + deploy)
4. Skips cadence sync when a build pipeline is already executing

Architecture:
- CadenceTimerThread runs as a daemon alongside the main request watcher
- Polling interval is configurable in days (default: 7 days, minimum 1 day)
- Cadence configuration is reloaded from build_stream_config.yml at the start
  of every cycle, so parameter changes apply without a service restart
- The latest cadence catalog is fetched from GitLab before each sync
- Pipeline idle check uses the NFS processing queue presence
- Catalog version bump follows semver patch increment (e.g., 1.0 -> 1.1)
- GitLab API operations use requests library to update cadence_catalog_rhel.json

ER Reference: ER-BSM-002 — AC-008, AC-009, AC-015
"""

import base64
import json
import logging
import os
import re
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread, Event
from typing import Optional, Dict, Any
from urllib.parse import quote

import requests
import yaml

logger = logging.getLogger(__name__)


# Cadence configuration defaults and fixed system contracts
SECONDS_PER_DAY = 86400
DEFAULT_CADENCE_INTERVAL_DAYS = 7
DEFAULT_CADENCE_INTERVAL_SECONDS = (
    DEFAULT_CADENCE_INTERVAL_DAYS * SECONDS_PER_DAY
)
DEFAULT_CADENCE_CATALOG_FILENAME = "cadence_catalog_rhel.json"
DEFAULT_CADENCE_PLAYBOOK_NAME = "repo_sync.yml"
DEFAULT_CADENCE_ENABLED = False
CADENCE_CONFIG_KEYS = {
    "enabled",
    "interval_days",
    "sync_timeout_seconds",
    "sync_poll_interval_seconds",
}
GITLAB_PROJECT_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")
IPV4_PATTERN = re.compile(
    r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
    r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)

# Cadence parameters reported by the per-cycle reload when they change
RELOAD_LOGGED_KEYS = (
    "enabled",
    "interval_days",
    "sync_timeout_seconds",
    "sync_poll_interval_seconds",
    "gitlab_host",
    "gitlab_https_port",
    "gitlab_project_name",
    "gitlab_default_branch",
)

# Cadence secrets reported as updated, never by value
RELOAD_LOGGED_SECRET_KEYS = (
    "gitlab_root_token",
    "gitlab_project_id",
)

# Audit event type for cadence sync completion
CADENCE_SYNC_COMPLETED = "CADENCE_SYNC_COMPLETED"


def _default_build_stream_config_path() -> Path:
    """Return the project-scoped BuildStream configuration path."""
    omnia_data_path = Path(os.getenv("OMNIA_DATA_PATH", "/opt/omnia"))
    project_name = os.getenv("OMNIA_PROJECT_NAME", "project_default")
    return (
        omnia_data_path
        / "build_stream"
        / "input"
        / project_name
        / "build_stream_config.yml"
    )


def _cadence_log_dir(job_id: str) -> Path:
    """Return the directory holding the cadence sync playbook log."""
    omnia_data_path = Path(os.getenv("OMNIA_DATA_PATH", "/opt/omnia"))
    return omnia_data_path / "build_stream" / "log" / job_id


def _repo_resync_status_path() -> Path:
    """Return the project-scoped Repo Manager resync result path."""
    omnia_data_path = Path(os.getenv("OMNIA_DATA_PATH", "/opt/omnia"))
    project_name = os.getenv("OMNIA_PROJECT_NAME", "project_default")
    return (
        omnia_data_path
        / "repo_manager"
        / "output"
        / project_name
        / "repo_resync_status.yml"
    )


def log_secure_info(
    level: str,
    message: str,
    identifier: Optional[str] = None,
    exc_info: bool = False,
) -> None:
    """Log information securely with optional identifier truncation.

    Args:
        level: Log level ('info', 'warning', 'error', 'debug', 'critical')
        message: Log message
        identifier: Optional identifier (first 8 chars logged)
        exc_info: If True, append current exception traceback
    """
    if identifier:
        log_message = f"{message}: {identifier[:8]}..."
    else:
        log_message = message
    log_func = getattr(logger, level)
    log_func(log_message, exc_info=exc_info)


def load_cadence_config(
    config_path: Optional[str] = None,
    credentials_path: Optional[str] = None,
    strict: bool = False,
) -> Dict[str, Any]:
    """Load cadence polling configuration from build_stream_config.yml.

    build_stream_config.yml is the single source of truth for cadence
    configuration; all settings are read from its "cadence" group.
    GitLab API credentials are loaded from build_stream_credentials.yml.

    Args:
        config_path: Path to config file. If None, uses environment
                    variables or default locations.
        credentials_path: Path to credentials file. If None, uses default.
        strict: Raise when the main configuration cannot be loaded. Reload
            callers use this to retain their last-known-good configuration.

    Returns:
        Dictionary with cadence configuration values.

    Raises:
        ValueError: If required configuration is missing or invalid.
    """
    if config_path is None:
        config_path = os.getenv(
            "BUILD_STREAM_CONFIG_PATH",
            str(_default_build_stream_config_path()),
        )

    if credentials_path is None:
        # Default credentials path (same directory as config)
        config_dir = Path(config_path).parent
        credentials_path = config_dir / "build_stream_credentials.yml"

    # Default configuration with operational parameters only
    config = {
        # Cadence polling control
        "enabled": DEFAULT_CADENCE_ENABLED,
        "interval_days": DEFAULT_CADENCE_INTERVAL_DAYS,
        # Timing parameters (configurable)
        "sync_timeout_seconds": 3600,
        "sync_poll_interval_seconds": 10,
        # GitLab API configuration (loaded from build_stream_config.yml)
        "gitlab_host": "",
        "gitlab_https_port": 443,
        "gitlab_project_name": "omnia-catalog",
        "gitlab_default_branch": "main",
        # Fixed values (not configurable)
        "auto_bump_version": True,
        "version_bump_strategy": "patch",
        "emit_audit_events": True,
        "log_level": "info",
    }

    if Path(config_path).exists():
        config = _load_unified_config(config_path, config, strict=strict)
    else:
        if strict:
            raise ValueError(
                f"BuildStream configuration does not exist: {config_path}"
            )
        log_secure_info(
            "info",
            "No build_stream_config.yml found, using cadence defaults"
        )

    # Load GitLab credentials if available
    if Path(credentials_path).exists():
        _load_gitlab_credentials(credentials_path, config, strict=strict)
    else:
        log_secure_info(
            "info",
            "No build_stream_credentials.yml found, GitLab API disabled"
        )

    return config


def _load_unified_config(
    config_path: str,
    defaults: Dict[str, Any],
    strict: bool = False,
) -> Dict[str, Any]:
    """Load cadence config from the "cadence" group of build_stream_config.yml.

    Args:
        config_path: Path to build_stream_config.yml
        defaults: Default configuration to merge with
        strict: Raise when the document or cadence mapping is invalid.

    Returns:
        Merged configuration dictionary.
    """
    config = dict(defaults)
    try:
        with open(config_path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)

        if not isinstance(data, dict):
            if strict:
                raise ValueError("BuildStream configuration is not a mapping")
            log_secure_info("warning", "Config is not a dictionary")
            return config

        cadence_section = data.get("cadence")
        if cadence_section is None:
            if strict:
                raise ValueError("BuildStream configuration has no cadence mapping")
            log_secure_info(
                "info",
                "No 'cadence' group in build_stream_config.yml, using defaults"
            )
            return config
        if not isinstance(cadence_section, dict):
            if strict:
                raise ValueError("BuildStream cadence configuration is not a mapping")
            log_secure_info(
                "warning", "'cadence' group is not a mapping, using defaults"
            )
            return config

        unknown_keys = set(cadence_section) - CADENCE_CONFIG_KEYS
        if unknown_keys:
            raise ValueError(
                "Unsupported cadence configuration fields: "
                f"{', '.join(sorted(unknown_keys))}"
            )

        # Only these parameters are user-configurable; the rest stay fixed
        bool_keys = ("enabled",)
        int_keys = (
            "interval_days",
            "sync_timeout_seconds",
            "sync_poll_interval_seconds",
        )

        for key in bool_keys:
            if key in cadence_section:
                value = cadence_section[key]
                if not isinstance(value, bool):
                    raise ValueError(f"Cadence {key} must be a boolean")
                config[key] = value

        for key in int_keys:
            if key in cadence_section:
                value = cadence_section[key]
                if not isinstance(value, int) or isinstance(value, bool):
                    raise ValueError(f"Cadence {key} must be an integer")
                if key == "interval_days" and value < 1:
                    raise ValueError(
                        "Cadence interval_days must be at least 1"
                    )
                if key == "sync_timeout_seconds" and value < 60:
                    raise ValueError(
                        "Cadence sync_timeout_seconds must be at least 60"
                    )
                if key == "sync_poll_interval_seconds" and not 1 <= value <= 300:
                    raise ValueError(
                        "Cadence sync_poll_interval_seconds must be between "
                        "1 and 300"
                    )
                config[key] = value

        # Load GitLab configuration from root level (not cadence section)
        _load_gitlab_config_fields(data, config)

        # Read through .get() so a caller-supplied partial defaults mapping
        # cannot turn this log line into an uncaught KeyError.
        log_secure_info(
            "info",
            f"Cadence config loaded from build_stream_config.yml: "
            f"enabled={config.get('enabled', DEFAULT_CADENCE_ENABLED)}, "
            f"interval="
            f"{config.get('interval_days', DEFAULT_CADENCE_INTERVAL_DAYS)}d"
        )
    except (OSError, ValueError, TypeError, yaml.YAMLError) as exc:
        if strict:
            raise ValueError(
                f"Failed to load cadence configuration {config_path}: {exc}"
            ) from exc
        log_secure_info(
            "error",
            "Failed to load cadence config, using defaults",
            exc_info=True,
        )
        return dict(defaults)

    return config


def _load_gitlab_config_fields(
    data: Dict[str, Any],
    config: Dict[str, Any],
) -> None:
    """Validate and load GitLab settings using the input-schema contract."""
    if "gitlab_host" in data:
        host = data["gitlab_host"]
        if not isinstance(host, str):
            raise ValueError("gitlab_host must be a string")
        if data.get("enable_build_stream") is True and not IPV4_PATTERN.fullmatch(
            host
        ):
            raise ValueError(
                "gitlab_host must be a valid IPv4 address when BuildStream "
                "is enabled"
            )
        config["gitlab_host"] = host

    if "gitlab_https_port" in data:
        port = data["gitlab_https_port"]
        if (
            not isinstance(port, int)
            or isinstance(port, bool)
            or not 1 <= port <= 65535
        ):
            raise ValueError("gitlab_https_port must be an integer from 1 to 65535")
        config["gitlab_https_port"] = port

    if "gitlab_project_name" in data:
        project_name = data["gitlab_project_name"]
        if (
            not isinstance(project_name, str)
            or not 1 <= len(project_name) <= 255
            or not GITLAB_PROJECT_NAME_PATTERN.fullmatch(project_name)
        ):
            raise ValueError("gitlab_project_name does not match the input schema")
        config["gitlab_project_name"] = project_name

    if "gitlab_default_branch" in data:
        branch = data["gitlab_default_branch"]
        if not isinstance(branch, str) or not branch:
            raise ValueError("gitlab_default_branch must be a non-empty string")
        config["gitlab_default_branch"] = branch


def _load_gitlab_credentials(
    credentials_path: str,
    config: Dict[str, Any],
    strict: bool = False,
) -> None:
    """Load GitLab API credentials from build_stream_credentials.yml.

    Handles both encrypted (Ansible Vault) and plain YAML files.
    For encrypted files, uses ansible-vault command with vault key file.

    Args:
        credentials_path: Path to build_stream_credentials.yml
        config: Config dictionary to update with credentials
        strict: Raise when credentials cannot be safely loaded.
    """
    try:
        # Check if file is Ansible Vault encrypted
        with open(credentials_path, "r", encoding="utf-8") as fh:
            first_line = fh.readline()

        if first_line.startswith("$ANSIBLE_VAULT"):
            # Encrypted - use ansible-vault to decrypt
            vault_key_path = Path(credentials_path).parent / ".build_stream_credentials_key"

            if not vault_key_path.exists():
                if strict:
                    raise ValueError(
                        f"Vault key not found for credentials: {credentials_path}"
                    )
                log_secure_info(
                    "warning",
                    f"Vault key not found at {vault_key_path}. "
                    "Cannot decrypt credentials. GitLab API disabled."
                )
                return

            # Decrypt using ansible-vault view command
            try:
                result = subprocess.run(
                    [
                        "ansible-vault",
                        "view",
                        str(credentials_path),
                        "--vault-password-file",
                        str(vault_key_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=True,
                )
                creds = yaml.safe_load(result.stdout)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                if strict:
                    raise ValueError("Failed to decrypt GitLab credentials") from exc
                log_secure_info(
                    "warning",
                    "Failed to decrypt credentials with ansible-vault",
                    exc_info=True,
                )
                return
        else:
            # Plain YAML - load directly
            with open(credentials_path, "r", encoding="utf-8") as fh:
                creds = yaml.safe_load(fh)

        if not isinstance(creds, dict):
            if strict:
                raise ValueError("Credentials file is not a mapping")
            log_secure_info("warning", "Credentials file is not a dictionary")
            return

        credential_updates: Dict[str, str] = {}
        if "gitlab_root_token" in creds:
            token = creds["gitlab_root_token"]
            if not isinstance(token, str) or not token.strip():
                raise ValueError("gitlab_root_token must be a non-empty string")
            credential_updates["gitlab_root_token"] = token

        if "gitlab_project_id" in creds:
            project_id = creds["gitlab_project_id"]
            if isinstance(project_id, bool) or not isinstance(
                project_id, (str, int)
            ):
                raise ValueError("gitlab_project_id must be a string or integer")
            normalized_project_id = str(project_id).strip()
            if not normalized_project_id:
                raise ValueError("gitlab_project_id must not be empty")
            credential_updates["gitlab_project_id"] = normalized_project_id

        config.update(credential_updates)

        log_secure_info(
            "info",
            f"GitLab credentials loaded: "
            f"token={'present' if config.get('gitlab_root_token') else 'missing'}, "
            f"project_id={'present' if config.get('gitlab_project_id') else 'missing'}"
        )

    except (OSError, ValueError, ImportError, yaml.YAMLError) as exc:
        if strict:
            raise ValueError(
                f"Failed to load GitLab credentials: {credentials_path}"
            ) from exc
        log_secure_info(
            "warning",
            "Failed to load GitLab credentials",
            exc_info=True,
        )


def is_pipeline_busy(processing_dir: Path) -> bool:
    """Check if a build pipeline is currently executing.

    Determines pipeline activity by checking for active requests in the
    NFS processing queue directory. If any .json files are present in
    the processing directory, a pipeline is considered active.

    Args:
        processing_dir: Path to the NFS processing queue directory.

    Returns:
        True if a build pipeline is currently executing, False otherwise.
    """
    try:
        if not processing_dir.exists():
            return False
        active_files = list(processing_dir.glob("*.json"))
        return len(active_files) > 0
    except OSError:
        log_secure_info(
            "warning",
            "Failed to check processing directory for active pipelines"
        )
        return True  # Assume busy on error (safe default)


def bump_catalog_version(catalog_path: Path) -> Optional[str]:
    """Bump the version field in the cadence catalog file.

    Increments the minor version (e.g., "1.0" -> "1.1", "1.5" -> "1.6").

    Args:
        catalog_path: Path to the cadence_catalog_rhel.json file.

    Returns:
        The new version string, or None on failure.
    """
    try:
        original_content = catalog_path.read_text(encoding="utf-8")
        new_version, catalog_content = _render_bumped_catalog(original_content)
        if not _write_text_atomically(catalog_path, catalog_content):
            return None

        log_secure_info(
            "info",
            f"Cadence catalog version bumped to {new_version}"
        )
        return new_version

    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        log_secure_info(
            "error",
            "Failed to bump cadence catalog version",
            exc_info=True,
        )
        return None


def _render_bumped_catalog(catalog_content: str) -> tuple[str, str]:
    """Return the next catalog version and serialized content without writing."""
    catalog_data = json.loads(catalog_content)
    if not isinstance(catalog_data, dict):
        raise ValueError("Cadence catalog must be a JSON object")

    catalog_section = catalog_data.get("catalog", {})
    if not isinstance(catalog_section, dict):
        raise ValueError("Cadence catalog.catalog must be a JSON object")
    current_version = catalog_section.get("version", "1.0")

    version_match = re.fullmatch(r"(\d+)\.(\d+)", str(current_version))
    if version_match:
        major = int(version_match.group(1))
        minor = int(version_match.group(2))
        new_version = f"{major}.{minor + 1}"
    else:
        new_version = f"{current_version}.1"

    catalog_section["version"] = new_version
    catalog_data["catalog"] = catalog_section
    return new_version, json.dumps(catalog_data, indent=2) + "\n"


def _write_text_atomically(target_path: Path, content: str) -> bool:
    """Replace a text file atomically without exposing partial content."""
    temporary_path: Optional[Path] = None
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            dir=target_path.parent,
            prefix=f".{target_path.name}.",
            suffix=".tmp",
            text=True,
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "w", encoding="utf-8") as temporary_file:
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, target_path)
        return True
    except OSError:
        log_secure_info(
            "error",
            f"Failed to atomically replace catalog: {target_path}",
            exc_info=True,
        )
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                log_secure_info(
                    "warning",
                    "Failed to remove temporary cadence catalog",
                    exc_info=True,
                )
        return False


def _validate_catalog_document(document: Any) -> bool:
    """Return whether a decoded document has the required catalog structure."""
    if not isinstance(document, dict):
        return False
    catalog = document.get("catalog")
    version = catalog.get("version") if isinstance(catalog, dict) else None
    return isinstance(version, str) and bool(
        re.fullmatch(r"\d+\.\d+(?:\.\d+)?", version)
    )


def fetch_cadence_catalog_from_gitlab(
    gitlab_url: str,
    gitlab_token: str,
    project_id: str,
    catalog_filename: str,
    branch: str,
    catalog_path: Path,
) -> bool:
    """Fetch, validate, and atomically install the cadence catalog."""
    encoded_project_id = quote(str(project_id), safe="")
    encoded_filename = quote(catalog_filename, safe="")
    api_url = (
        f"{gitlab_url}/api/v4/projects/{encoded_project_id}"
        f"/repository/files/{encoded_filename}/raw"
    )
    headers = {"PRIVATE-TOKEN": gitlab_token}

    try:
        response = requests.get(
            api_url,
            headers=headers,
            params={"ref": branch},
            verify=False,  # nosec B501 - Match existing internal GitLab TLS behavior
            timeout=30,
        )
        if response.status_code != 200:
            log_secure_info(
                "warning",
                "GitLab cadence catalog fetch failed with status "
                f"{response.status_code}",
            )
            return False

        try:
            document = json.loads(response.text)
        except json.JSONDecodeError:
            log_secure_info(
                "warning",
                "GitLab cadence catalog is not valid JSON; local catalog preserved",
            )
            return False

        if not _validate_catalog_document(document):
            log_secure_info(
                "warning",
                "GitLab cadence catalog has an invalid structure; "
                "local catalog preserved",
            )
            return False

        if not _write_text_atomically(catalog_path, response.text):
            return False

        log_secure_info(
            "info",
            "Cadence catalog fetched from GitLab and installed atomically",
        )
        return True
    except requests.RequestException:
        log_secure_info(
            "warning",
            "GitLab cadence catalog fetch request failed; local catalog preserved",
            exc_info=True,
        )
        return False


def update_catalog_via_gitlab_api(
    gitlab_url: str,
    gitlab_token: str,
    project_id: str,
    catalog_filename: str,
    catalog_content: str,
    new_version: str,
    branch: str = "main",
) -> bool:
    """Update cadence catalog in GitLab via API.

    Args:
        gitlab_url: GitLab base URL (e.g., https://gitlab.example.com)
        gitlab_token: GitLab API token
        project_id: GitLab project ID
        catalog_filename: Filename in repo (e.g., cadence_catalog_rhel.json)
        catalog_content: New file content (JSON string)
        new_version: Version for commit message
        branch: Target branch (default: main)

    Returns:
        True if update succeeded, False otherwise.
    """
    # URL-encode the filename (replace / with %2F)
    encoded_filename = quote(catalog_filename, safe='')
    encoded_project_id = quote(str(project_id), safe="")
    api_url = (
        f"{gitlab_url}/api/v4/projects/{encoded_project_id}"
        f"/repository/files/{encoded_filename}"
    )

    headers = {
        "PRIVATE-TOKEN": gitlab_token,
        "Content-Type": "application/json"
    }

    # Base64 encode the content
    content_base64 = base64.b64encode(catalog_content.encode()).decode()

    payload = {
        "branch": branch,
        "encoding": "base64",
        "content": content_base64,
        "commit_message": f"chore(cadence): bump catalog version to {new_version}"
    }

    try:
        # Use PUT to update existing file
        response = requests.put(
            api_url,
            headers=headers,
            json=payload,
            verify=False,  # nosec B501 - Match existing TLS behavior in GitLab roles
            timeout=30
        )

        if response.status_code in [200, 201]:
            log_secure_info(
                "info",
                f"Cadence catalog updated via GitLab API: v{new_version}"
            )
            return True
        else:
            log_secure_info(
                "error",
                f"GitLab API update failed: {response.status_code} "
                f"{response.text[:200]}"
            )
            return False

    except requests.RequestException:
        log_secure_info(
            "error",
            "GitLab API request failed",
            exc_info=True
        )
        return False


def copy_cadence_catalog_to_default_path(
    cadence_catalog_path: Path,
    catalog_path: Path,
) -> bool:
    """Copy the cadence catalog to the configured CATALOG_FILE_PATH.

    The repo_sync.yml playbook uses CATALOG_FILE_PATH to determine which
    packages to sync. This function ensures the cadence catalog is available
    at that path before triggering the sync.

    Args:
        cadence_catalog_path: Path to the cadence_catalog_rhel.json file.
        catalog_path: Path selected by the CATALOG_FILE_PATH environment variable.

    Returns:
        True if copy succeeded, False otherwise.
    """
    try:
        if not cadence_catalog_path.exists():
            log_secure_info(
                "error",
                f"Cadence catalog not found: {cadence_catalog_path}"
            )
            return False

        # Ensure target directory exists
        catalog_path.parent.mkdir(parents=True, exist_ok=True)

        # Copy cadence catalog to the configured path
        with open(cadence_catalog_path, "r", encoding="utf-8") as src:
            catalog_data = json.load(src)

        with open(catalog_path, "w", encoding="utf-8") as dst:
            json.dump(catalog_data, dst, indent=2)
            dst.write("\n")

        log_secure_info(
            "info",
            "Cadence catalog copied to CATALOG_FILE_PATH"
        )
        return True

    except (OSError, json.JSONDecodeError):
        log_secure_info(
            "error",
            "Failed to copy cadence catalog to CATALOG_FILE_PATH",
            exc_info=True,
        )
        return False


def submit_repo_sync_request(
    requests_dir: Path,
    job_id: str,
) -> bool:
    """Submit a repo sync request to the NFS playbook queue.

    Creates a JSON request file in the requests directory that the
    playbook watcher will pick up and execute. The playbook uses
    CATALOG_FILE_PATH to determine which packages to sync.

    Args:
        requests_dir: Path to the NFS playbook queue requests directory.
        job_id: Unique job ID for this cadence sync request.
    Returns:
        True if the request was submitted successfully, False otherwise.
    """
    request_data = {
        "job_id": job_id,
        "stage_name": "cadence-repo-sync",
        "playbook_path": DEFAULT_CADENCE_PLAYBOOK_NAME,
        "correlation_id": job_id,
        "extra_vars": {
            "job_id": job_id,
            "cadence_sync": True,
        },
    }

    request_filename = f"cadence-sync-{job_id}.json"
    request_path = requests_dir / request_filename

    try:
        with open(request_path, "w", encoding="utf-8") as fh:
            json.dump(request_data, fh, indent=2)

        log_secure_info(
            "info",
            "Submitted cadence repo sync request",
            job_id
        )
        return True
    except OSError:
        log_secure_info(
            "error",
            "Failed to submit cadence repo sync request",
            job_id
        )
        return False


def wait_for_sync_result(
    results_dir: Path,
    job_id: str,
    timeout_seconds: int = 3600,
    poll_interval: int = 10,
) -> Optional[Dict[str, Any]]:
    """Wait for the repo sync playbook result file.

    Polls the results directory for the expected result file.

    Args:
        results_dir: Path to the NFS playbook queue results directory.
        job_id: Job ID to match against result files.
        timeout_seconds: Maximum time to wait for result (default: 1 hour).
        poll_interval: Seconds between polls (default: 10).

    Returns:
        The result data dictionary if found, None on timeout.
    """
    request_filename = f"cadence-sync-{job_id}.json"
    result_paths = (
        results_dir / request_filename,
        results_dir.parent / "archive" / "results" / request_filename,
    )
    start_time = time.monotonic()

    while (time.monotonic() - start_time) < timeout_seconds:
        result_path = next(
            (path for path in result_paths if path.exists()),
            None,
        )
        if result_path is not None:
            try:
                with open(result_path, "r", encoding="utf-8") as fh:
                    result_data = json.load(fh)
                log_secure_info(
                    "info",
                    f"Cadence sync result received: "
                    f"status={result_data.get('status', 'unknown')}",
                    job_id,
                )
                return result_data
            except (json.JSONDecodeError, OSError):
                log_secure_info(
                    "error",
                    "Failed to read cadence sync result file",
                    job_id,
                )
                return None

        time.sleep(poll_interval)

    log_secure_info(
        "warning",
        f"Cadence sync result timeout after {timeout_seconds}s",
        job_id,
    )
    return None


def load_repo_resync_status(status_path: Path) -> Optional[Dict[str, Any]]:
    """Load and validate the Repo Manager exact-mirror result contract."""
    try:
        with open(status_path, "r", encoding="utf-8") as status_file:
            status = yaml.safe_load(status_file)
    except (OSError, ImportError, yaml.YAMLError):
        log_secure_info(
            "error",
            f"Failed to read Repo Manager resync status: {status_path}",
            exc_info=True,
        )
        return None

    if not isinstance(status, dict):
        log_secure_info("error", "Repo Manager resync status is not a mapping")
        return None

    repositories = status.get("repositories")
    if (
        status.get("overall_status") != "success"
        or status.get("orphan_cleanup") != "success"
        or not isinstance(repositories, dict)
        or not repositories
    ):
        log_secure_info(
            "error",
            "Repo Manager resync status does not report aggregate success",
        )
        return None

    for repository_name, repository_result in repositories.items():
        if not isinstance(repository_result, dict):
            log_secure_info(
                "error",
                f"Invalid resync result for repository {repository_name}",
            )
            return None
        if (
            repository_result.get("sync_status") != "success"
            or repository_result.get("cleanup_status") != "success"
            or repository_result.get("stale_packages_remaining") != 0
        ):
            log_secure_info(
                "error",
                f"Repository reconciliation is incomplete: {repository_name}",
            )
            return None
        for metric in ("packages_added", "packages_removed"):
            metric_value = repository_result.get(metric)
            if (
                not isinstance(metric_value, int)
                or isinstance(metric_value, bool)
                or metric_value < 0
            ):
                log_secure_info(
                    "error",
                    f"Invalid {metric} value for repository {repository_name}",
                )
                return None

    return status


def repo_resync_has_package_updates(status: Dict[str, Any]) -> bool:
    """Return whether the exact-mirror result added or removed RPM packages."""
    repositories = status.get("repositories", {})
    return any(
        int(result.get("packages_added", 0)) > 0
        or int(result.get("packages_removed", 0)) > 0
        for result in repositories.values()
    )


def emit_audit_event(
    event_type: str,
    details: Dict[str, Any],
) -> None:
    """Emit an audit event for cadence operations.

    Args:
        event_type: Audit event type (e.g., CADENCE_SYNC_COMPLETED).
        details: Event details dictionary.
    """
    audit_entry = {
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": details,
    }
    log_secure_info(
        "info",
        f"AUDIT: {event_type} — {json.dumps(audit_entry)}"
    )


class CadenceTimerThread(Thread):
    """Daemon thread that periodically triggers cadence builds.

    The cadence timer:
    1. Sleeps for the configured interval (default: 7 days)
    2. Reloads cadence configuration and credentials
    3. Checks if a build pipeline is currently executing
    4. If idle, submits a repo_manager sync request
    5. Waits for sync completion
    6. On success, bumps catalog version and pushes to GitLab
    7. Emits CADENCE_SYNC_COMPLETED audit event

    Attributes:
        interval_seconds: Polling interval converted from configured days.
        catalog_filename: Fixed cadence catalog file in GitLab.
        gitlab_url: GitLab base URL.
        gitlab_token: GitLab API token.
        gitlab_project_id: GitLab project ID.
        gitlab_branch: GitLab branch name.
        requests_dir: NFS playbook queue requests directory.
        results_dir: NFS playbook queue results directory.
        processing_dir: NFS playbook queue processing directory.
        stop_event: Event to signal graceful shutdown.
        trigger_event: Event to request an immediate cadence cycle.
    """

    def __init__(
        self,
        config: Dict[str, Any],
        requests_dir: Path,
        results_dir: Path,
        processing_dir: Path,
    ) -> None:
        """Initialize the cadence timer thread.

        Args:
            config: Cadence configuration dictionary.
            requests_dir: Path to NFS requests directory.
            results_dir: Path to NFS results directory.
            processing_dir: Path to NFS processing directory.

        Raises:
            ValueError: If required GitLab configuration is missing.
        """
        super().__init__(name="CadenceTimerThread", daemon=True)
        self.requests_dir: Path = requests_dir
        self.results_dir: Path = results_dir
        self.processing_dir: Path = processing_dir
        self.stop_event: Event = Event()
        self.trigger_event: Event = Event()
        self.catalog_filename = DEFAULT_CADENCE_CATALOG_FILENAME
        self.config: Dict[str, Any] = {}
        self.enabled = DEFAULT_CADENCE_ENABLED
        self.interval_days = DEFAULT_CADENCE_INTERVAL_DAYS
        self.interval_seconds = DEFAULT_CADENCE_INTERVAL_SECONDS
        self.gitlab_url = ""
        self.gitlab_project_name = "omnia-catalog"
        self.gitlab_branch = "main"
        self.gitlab_token = ""
        self.gitlab_project_id = ""
        self._apply_config(config)

    def _apply_config(self, config: Dict[str, Any]) -> None:
        """Apply one validated cadence configuration snapshot."""
        self.config = dict(config)
        self.enabled = bool(config.get("enabled", DEFAULT_CADENCE_ENABLED))
        self.interval_days = int(
            config.get("interval_days", DEFAULT_CADENCE_INTERVAL_DAYS)
        )
        self.interval_seconds = self.interval_days * SECONDS_PER_DAY

        # Load GitLab configuration from build_stream_config.yml
        gitlab_host = config.get("gitlab_host", "")
        gitlab_port = config.get("gitlab_https_port", 443)
        self.gitlab_url = (
            f"https://{gitlab_host}:{gitlab_port}" if gitlab_host else ""
        )
        self.gitlab_project_name = config.get(
            "gitlab_project_name", "omnia-catalog"
        )
        self.gitlab_branch = config.get("gitlab_default_branch", "main")

        # GitLab token must be loaded from credentials file
        # For now, we'll make it optional and log a warning if missing
        self.gitlab_token = config.get("gitlab_root_token", "")
        self.gitlab_project_id = config.get("gitlab_project_id", "")

        # Validate required GitLab configuration (warning only, not fatal)
        if not self.gitlab_url or not self.gitlab_token or not self.gitlab_project_id:
            log_secure_info(
                "warning",
                "GitLab configuration incomplete for cadence polling. "
                "Catalog updates to GitLab will be skipped. "
                "Configure gitlab_host, gitlab_root_token, and gitlab_project_id "
                "in build_stream_config.yml or build_stream_credentials.yml"
            )

    def _reload_config(self) -> bool:
        """Reload cadence settings while retaining the last-known-good state."""
        try:
            reloaded = load_cadence_config(strict=True)
        except ValueError as exc:
            log_secure_info(
                "warning",
                f"Cadence configuration reload failed; retaining running "
                f"values: {exc}",
            )
            return False

        # A temporarily unreadable credentials file must not erase credentials
        # already held by the running watcher.
        for key in ("gitlab_root_token", "gitlab_project_id"):
            if not reloaded.get(key) and self.config.get(key):
                reloaded[key] = self.config[key]

        previous = self.config
        self._apply_config(reloaded)
        self._log_config_changes(previous, self.config)
        return True

    @staticmethod
    def _log_config_changes(
        previous: Dict[str, Any],
        current: Dict[str, Any],
    ) -> None:
        """Log cadence parameters that changed during a reload.

        Only changed keys are logged, so a stable configuration does not emit
        a log line on every cycle. Secret values are reported as updated and
        are never written to the log.

        Args:
            previous: Configuration in effect before the reload.
            current: Configuration applied by the reload.
        """
        for key in RELOAD_LOGGED_KEYS:
            if previous.get(key) != current.get(key):
                log_secure_info(
                    "info",
                    f"Cadence config reloaded: {key} "
                    f"{previous.get(key)} -> {current.get(key)}"
                )

        for secret_key in RELOAD_LOGGED_SECRET_KEYS:
            if previous.get(secret_key) != current.get(secret_key):
                log_secure_info(
                    "info",
                    f"Cadence config reloaded: {secret_key} updated"
                )

    def _gitlab_configuration_complete(self) -> bool:
        """Return whether all GitLab API values required by cadence exist."""
        return all(
            (
                self.gitlab_url,
                self.gitlab_token,
                self.gitlab_project_id,
                self.gitlab_branch,
            )
        )

    def _refresh_catalog_from_gitlab(self) -> bool:
        """Refresh the local cadence catalog without destroying fallback data."""
        if not self._gitlab_configuration_complete():
            log_secure_info(
                "warning",
                "GitLab configuration incomplete; cadence catalog fetch skipped "
                "and existing local catalog preserved",
            )
            return False

        catalog_file_path = os.getenv("CATALOG_FILE_PATH")
        if not catalog_file_path:
            log_secure_info(
                "warning",
                "CATALOG_FILE_PATH is not set; GitLab cadence catalog fetch skipped",
            )
            return False

        return fetch_cadence_catalog_from_gitlab(
            self.gitlab_url,
            self.gitlab_token,
            self.gitlab_project_id,
            self.catalog_filename,
            self.gitlab_branch,
            Path(catalog_file_path),
        )

    def run(self) -> None:
        """Main cadence polling loop.

        Waits for either the configured interval to elapse or a manual
        trigger (via SIGUSR1 / ``trigger()``), whichever comes first.
        """
        log_secure_info(
            "info",
            f"CadenceTimerThread started: "
            f"interval={self.interval_days}d, "
            f"catalog={self.catalog_filename}"
        )

        while not self.stop_event.is_set():
            # Wait for interval OR manual trigger, whichever comes first.
            # interval_seconds is re-read on every iteration, so a value
            # reloaded during the previous cycle takes effect here without a
            # service restart. SIGUSR1 applies a new interval immediately.
            triggered = self.trigger_event.wait(
                timeout=self.interval_seconds
            )
            if self.stop_event.is_set():
                log_secure_info(
                    "info",
                    "CadenceTimerThread shutdown requested"
                )
                break
            if triggered:
                self.trigger_event.clear()
                log_secure_info(
                    "info",
                    "Manual cadence trigger received — "
                    "executing cycle immediately"
                )

            self._execute_cadence_cycle()

        log_secure_info("info", "CadenceTimerThread stopped")

    def stop(self) -> None:
        """Signal the cadence timer to stop."""
        self.stop_event.set()
        # Wake up the trigger_event so the thread exits promptly
        self.trigger_event.set()

    def trigger(self) -> None:
        """Trigger an immediate cadence cycle.

        Called from the SIGUSR1 signal handler to bypass the polling
        interval and execute a cadence cycle right away.
        """
        log_secure_info(
            "info", "Cadence manual trigger requested via SIGUSR1"
        )
        self.trigger_event.set()

    def _execute_cadence_cycle(self) -> None:
        """Execute one cadence polling cycle."""
        log_secure_info("info", "Cadence polling cycle started")

        # Step 1: Reload operator settings without restarting the service.
        self._reload_config()
        if not self.enabled:
            log_secure_info(
                "info",
                "Cadence polling is disabled; cycle skipped and timer remains active",
            )
            return

        # Step 2: Check if pipeline is busy (AC-009)
        if is_pipeline_busy(self.processing_dir):
            log_secure_info(
                "info",
                "Cadence sync suppressed — build pipeline in progress"
            )
            return

        # Step 3: Fetch the operator-controlled catalog from GitLab. Fetch
        # failure is non-blocking and leaves the existing local catalog intact.
        self._refresh_catalog_from_gitlab()

        # Step 4-5: Sync packages via repo_manager
        sync_result = self._sync_packages()
        if sync_result is None:
            return

        job_id = str(sync_result["job_id"])
        updates_detected = bool(sync_result["updates_detected"])
        if updates_detected:
            log_secure_info(
                "info", "Package count changes detected in cadence sync"
            )
        else:
            log_secure_info(
                "info",
                "No package count change detected; running the full cadence "
                "pipeline because upstream package versions may have changed",
            )

        # Always bump and trigger after successful exact-mirror reconciliation.
        # Package add/remove counts cannot detect version-only RPM updates.
        self._bump_and_push(job_id)

    def _sync_packages(self) -> Optional[Dict[str, Any]]:
        """Submit repo sync and wait for completion.

        Steps:
        1. Copy cadence catalog to CATALOG_FILE_PATH
        2. Submit repo_sync.yml playbook request
        3. Wait for sync completion

        Returns:
            Sync outcome on success, None on failure.
        """
        job_id = f"cadence-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        # Step 1: Submit repo_sync.yml playbook request
        if not submit_repo_sync_request(
            self.requests_dir,
            job_id,
        ):
            log_secure_info("error", "Failed to submit repo sync request")
            return None

        # Step 2: Wait for sync completion
        result = wait_for_sync_result(
            self.results_dir,
            job_id,
            timeout_seconds=int(
                self.config.get("sync_timeout_seconds", 3600)
            ),
            poll_interval=int(
                self.config.get("sync_poll_interval_seconds", 10)
            ),
        )
        if result is None:
            log_secure_info(
                "error",
                f"Repo sync did not complete in time; "
                f"log_dir={_cadence_log_dir(job_id)}"
            )
            return None

        log_file = result.get("log_file_path") or (
            f"N/A (see {_cadence_log_dir(job_id)})"
        )
        if result.get("status") != "success":
            log_secure_info(
                "warning",
                f"Repo sync failed: "
                f"{result.get('error_summary', 'unknown error')}; "
                f"log_file={log_file}"
            )
            return None

        log_secure_info(
            "info", f"Repo sync succeeded; log_file={log_file}"
        )

        repo_resync_status = load_repo_resync_status(
            _repo_resync_status_path()
        )
        if repo_resync_status is None:
            return None

        return {
            "job_id": job_id,
            "updates_detected": repo_resync_has_package_updates(
                repo_resync_status
            ),
            "repo_resync_status": repo_resync_status,
        }

    def _bump_and_push(self, job_id: str) -> bool:
        """Bump catalog version, push to GitLab, and emit audit event.

        Args:
            job_id: The cadence sync job identifier.

        Returns:
            True only when the remote GitLab update succeeds.
        """
        if not self._gitlab_configuration_complete():
            log_secure_info(
                "error",
                "GitLab configuration incomplete; cadence catalog was not bumped",
            )
            return False

        # Read the current catalog from CATALOG_FILE_PATH
        catalog_file_path = os.getenv("CATALOG_FILE_PATH")
        if not catalog_file_path:
            log_secure_info(
                "error",
                "CATALOG_FILE_PATH environment variable not set"
            )
            return False

        catalog_path = Path(catalog_file_path)
        if not catalog_path.exists():
            log_secure_info(
                "error",
                f"Cadence catalog not found: {catalog_path}"
            )
            return False

        try:
            original_catalog_content = catalog_path.read_text(encoding="utf-8")
            new_version, catalog_content = _render_bumped_catalog(
                original_catalog_content
            )
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            log_secure_info(
                "error",
                "Failed to prepare cadence catalog version bump",
                exc_info=True,
            )
            return False

        if not update_catalog_via_gitlab_api(
            self.gitlab_url,
            self.gitlab_token,
            self.gitlab_project_id,
            self.catalog_filename,
            catalog_content,
            new_version,
            self.gitlab_branch,
        ):
            log_secure_info(
                "error",
                "Failed to push cadence catalog to GitLab; local catalog preserved",
            )
            return False

        if not _write_text_atomically(catalog_path, catalog_content):
            log_secure_info(
                "critical",
                "GitLab cadence catalog was updated but the matching local "
                "catalog could not be installed",
            )
            return False

        emit_audit_event(
            CADENCE_SYNC_COMPLETED,
            {
                "job_id": job_id,
                "catalog_filename": self.catalog_filename,
                "new_version": new_version,
                "sync_status": "success",
            },
        )

        log_secure_info(
            "info",
            f"Cadence cycle completed: catalog {self.catalog_filename} "
            f"bumped to v{new_version}"
        )
        return True
