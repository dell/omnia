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

"""
Build Stream — Shared Functions.

Config reading helpers, SSH to GitLab, credential access,
and other shared utilities used across pipeline automation.

Adapted from automation_v22/automation_library/build_stream/functions/shared_func.py
to use omnia_auto instead of automation_library.core.
"""

from typing import Any, Dict

import pytest

from omnia_auto import (
    run_on_host,
    load_test_config,
    load_test_credentials,
)

from ..vars.common_vars import CATALOG_DEFAULT_FILENAME


# =============================================================================
# CACHING
# =============================================================================

_credentials_cache: Dict[str, str] = {}


def clear_cache():
    """Clear all caches."""
    _credentials_cache.clear()


# =============================================================================
# BUILD STREAM CONFIGURATION READING FUNCTIONS
# =============================================================================

def get_build_stream_host_ip(host=None) -> str:
    """Get build_stream host IP from test config."""
    config = load_test_config()
    return config.get("bsm_host_ip", "") or ""


def get_build_stream_port(host=None) -> int:
    """Get build_stream API port from test config."""
    config = load_test_config()
    return config.get("bsm_api_port", 8010)


# =============================================================================
# GITLAB CONFIGURATION READING FUNCTIONS
# =============================================================================

def get_gitlab_host(host=None) -> str:
    """Get gitlab_host from test config."""
    config = load_test_config()
    return config.get("gitlab_host", "") or ""


def get_gitlab_https_port(host=None) -> int:
    """Get gitlab_https_port from test config."""
    config = load_test_config()
    return config.get("gitlab_https_port", 443)


def get_gitlab_project_name(host=None) -> str:
    """Get gitlab_project_name from test config."""
    config = load_test_config()
    return config.get("gitlab_project_name", "") or ""


def get_gitlab_default_branch(host=None) -> str:
    """Get gitlab_default_branch from test config."""
    config = load_test_config()
    return config.get("gitlab_default_branch", "main")


# =============================================================================
# CREDENTIAL FUNCTIONS
# =============================================================================

def get_postgres_user(host=None) -> str:
    """Get postgres_user from test credentials, fallback to 'omnia'."""
    cache_key = "postgres_user"
    if cache_key in _credentials_cache:
        return _credentials_cache[cache_key]

    try:
        creds = load_test_credentials()
        user = creds.get("postgres_user", "omnia") if creds else "omnia"
    except Exception:
        user = "omnia"

    _credentials_cache[cache_key] = user or "omnia"
    return _credentials_cache[cache_key]


# =============================================================================
# OMNIA TEST CONFIG FUNCTIONS
# =============================================================================

def get_allow_pipeline_cancel(host=None) -> bool:
    """Get allow_pipeline_cancel from test config. Default: False."""
    config = load_test_config()
    return config.get("allow_pipeline_cancel", False)


def get_image_identifier(host=None) -> str:
    """Get image_identifier from test config for deploy/cleanup selection."""
    config = load_test_config()
    return config.get("image_identifier", "") or ""


def get_catalog_name(host=None) -> str:
    """Get catalog_name from test config, fallback to default."""
    config = load_test_config()
    catalog = config.get("catalog_name", "") or ""
    return catalog if catalog else CATALOG_DEFAULT_FILENAME


def get_omnia_branch(host=None) -> str:
    """Get omnia_branch from test config for repo clone."""
    config = load_test_config()
    return config.get("omnia_branch", "") or ""


# =============================================================================
# SSH COMMAND EXECUTION (to GitLab server)
# =============================================================================

def ssh_to_gitlab(host, command: str) -> Dict[str, Any]:
    """
    Execute command on GitLab server via SSH.

    Args:
        host: Testinfra host object
        command: Command to execute on GitLab server

    Returns:
        Dict with success, rc, stdout, stderr, error keys
    """
    result = {
        "success": False,
        "rc": -1,
        "stdout": "",
        "stderr": "",
        "error": "",
    }

    gitlab_host = get_gitlab_host(host)
    if not gitlab_host:
        result["error"] = "gitlab_host not configured in test_config.yml"
        return result

    ssh_cmd = (
        f"ssh -o StrictHostKeyChecking=no -o BatchMode=yes "
        f"-o ConnectTimeout=10 "
        f"root@{gitlab_host} '{command}'"
    )

    cmd = run_on_host(host, ssh_cmd)
    result["rc"] = cmd.rc
    result["stdout"] = cmd.stdout.strip() if cmd.stdout else ""
    result["stderr"] = cmd.stderr.strip() if cmd.stderr else ""
    result["success"] = cmd.rc == 0

    if cmd.rc != 0:
        result["error"] = result["stderr"] or f"Command failed with rc={cmd.rc}"

    return result


def run_in_container(host, command: str, container: str = "omnia_core"):
    """
    Execute command inside a podman container on the target host.

    Args:
        host: Testinfra host object
        command: Command to execute inside the container
        container: Container name (default: omnia_core)

    Returns:
        Command result object with rc, stdout, stderr.
    """
    return run_on_host(host, f"podman exec {container} {command}")


# =============================================================================
# PSQL QUERY EXECUTION
# =============================================================================

def exec_psql_query(
    host, container: str, db_user: str, db_name: str, sql: str,
) -> Dict[str, Any]:
    """
    Execute a SQL query on PostgreSQL inside the container.

    Args:
        host: Testinfra host object
        container: PostgreSQL container name
        db_user: Database user
        db_name: Database name
        sql: SQL query string

    Returns:
        Dict with 'success', 'rows' (list of strings), 'error'.
    """
    result = {
        "success": False,
        "rows": [],
        "error": "",
    }

    cmd_str = (
        f"podman exec -e PGPASSWORD=Dell1234 {container} "
        f"psql -U {db_user} -d {db_name} -t -A -F'|' "
        f"-c \"{sql}\" 2>/dev/null"
    )

    cmd = run_on_host(host, cmd_str)
    if cmd.rc != 0:
        result["error"] = f"psql query failed (rc={cmd.rc})"
        return result

    stdout = cmd.stdout.strip() if cmd.stdout else ""
    if stdout:
        result["rows"] = [
            line.strip() for line in stdout.splitlines()
            if line.strip()
        ]

    result["success"] = True
    return result


# =============================================================================
# TEST HELPER FUNCTIONS
# =============================================================================

def skip_if_build_stream_not_enabled(host, log):
    """Skip test if build_stream is not enabled."""
    from .build_stream_func import is_build_stream_enabled
    if not is_build_stream_enabled(host):
        log.skipped(
            "build_stream is not enabled (enable_build_stream=false)",
            "Test skipped - build_stream not enabled"
        )
        pytest.skip("build_stream is not enabled")
