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
Build Stream — GitLab Server Access Helpers.

Read the GitLab settings from build_stream_config.yml, run commands on the
GitLab server over SSH from the OIM, fetch the GitLab root token and build a
TLS context that verifies GitLab.

SSH uses the key and the pinned host key that build_stream.yml sets up
(gitlab_passwordless_ssh), so no password is needed or handled here.
"""

import shlex
import ssl
from typing import Any, Dict

from omnia_auto import read_remote_yaml, run_on_host

from library.vars.common_vars import (
    CMDS,
    GITLAB_CA_CERT,
    GITLAB_ROOT_TOKEN_FILE,
    GITLAB_SSH_KEY,
)

from .http_func import http_status, tls_from_pem

from ._config_helpers import resolve_build_stream_input_path


def _get_gitlab_config_path(host) -> str:
    """Return the resolved path to build_stream_config.yml on the target host."""
    return f"{resolve_build_stream_input_path(host)}/build_stream_config.yml"


def get_gitlab_config(host) -> Dict[str, str]:
    """Read gitlab-related values from build_stream_config.yml.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict of configuration values. Includes '_config_path' key for
        error reporting.
    """
    config_path = _get_gitlab_config_path(host)
    values = {"_config_path": config_path}
    try:
        config = read_remote_yaml(host, config_path)
    except (OSError, RuntimeError, ValueError):
        return values
    values.update({key: str(value) for key, value in config.items()})
    return values


def ssh_to_gitlab(host, cmd: str) -> Dict[str, Any]:
    """Run a command on the GitLab server via SSH from the OIM.

    Uses the OIM -> GitLab key and the pinned host key that build_stream.yml
    installs (BatchMode, strict host key checking).

    Args:
        host: Testinfra host connection.
        cmd: Command to run on the GitLab server.

    Returns:
        Dict with keys: success, stdout, error.
    """
    gitlab_config = get_gitlab_config(host)
    gitlab_host = gitlab_config.get("gitlab_host", "")
    gitlab_user = gitlab_config.get("gitlab_ansible_user", "root") or "root"

    if not gitlab_host:
        config_path = gitlab_config.get("_config_path", "unknown")
        return {
            "success": False,
            "stdout": "",
            "error": (
                f"gitlab_host not found or empty in {config_path}. "
                f"Set gitlab_host in build_stream_config.yml."
            ),
        }

    ssh_cmd = CMDS["ssh_to_gitlab_key"].format(
        key=shlex.quote(GITLAB_SSH_KEY),
        gitlab_user=shlex.quote(gitlab_user),
        gitlab_host=shlex.quote(gitlab_host),
        cmd=shlex.quote(cmd),
    )
    result = run_on_host(host, ssh_cmd)

    if result.rc == 0:
        return {
            "success": True,
            "stdout": result.stdout if result.stdout else "",
            "error": "",
        }

    return {
        "success": False,
        "stdout": result.stdout if result.stdout else "",
        "error": (
            f"SSH to {gitlab_host} failed (rc={result.rc}). Verify the key "
            f"{GITLAB_SSH_KEY} that build_stream.yml --tags execute sets up."
        ),
    }


_GITLAB_TLS_CACHE: Dict[str, ssl.SSLContext] = {}


def gitlab_tls(host) -> ssl.SSLContext:
    """Return a TLS context that verifies GitLab against its hosted CA (cached).

    Raises:
        RuntimeError: When the CA cannot be read from the GitLab host or is invalid.
    """
    gitlab_host = get_gitlab_config(host).get("gitlab_host", "")
    if gitlab_host in _GITLAB_TLS_CACHE:
        return _GITLAB_TLS_CACHE[gitlab_host]
    result = ssh_to_gitlab(host, f"cat {GITLAB_CA_CERT}")
    if not result["success"] or "BEGIN CERTIFICATE" not in result["stdout"]:
        raise RuntimeError(f"GitLab CA {GITLAB_CA_CERT} could not be read from "
                           f"{gitlab_host or 'the GitLab host'}: {result['error']}")
    try:
        context = tls_from_pem(result["stdout"])
    except ssl.SSLError as exc:
        raise RuntimeError(f"GitLab CA {GITLAB_CA_CERT} is invalid: {exc}") from exc
    _GITLAB_TLS_CACHE[gitlab_host] = context
    return context


def get_gitlab_root_token(host) -> Dict[str, Any]:
    """Get the GitLab root access token from the GitLab server.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, token, error.
    """
    ssh_result = ssh_to_gitlab(
        host,
        f"cat {GITLAB_ROOT_TOKEN_FILE} 2>/dev/null",
    )
    if ssh_result["success"] and ssh_result["stdout"].strip():
        return {
            "success": True,
            "token": ssh_result["stdout"].strip(),
            "error": "",
        }
    if not ssh_result["success"]:
        return {
            "success": False,
            "token": "",
            "error": ssh_result["error"],
        }
    return {
        "success": False,
        "token": "",
        "error": "Root token not found",
    }


def gitlab_package_installed(host, package: str) -> bool:
    """Return whether ``rpm -q`` on the GitLab server lists ``package``."""
    ssh_result = ssh_to_gitlab(host, CMDS["rpm_check"].format(package=package))
    return ssh_result["success"] and package in ssh_result.get("stdout", "")


def gitlab_service_state(host, service: str, unreachable: str) -> str:
    """Return ``systemctl is-active`` of ``service`` on the GitLab server.

    ``unreachable`` is returned when the SSH command itself fails.
    """
    ssh_result = ssh_to_gitlab(host, CMDS["systemctl_is_active"].format(service=service))
    return ssh_result["stdout"].strip() if ssh_result["success"] else unreachable


def probe_gitlab_url(host) -> Dict[str, Any]:
    """Return the GitLab URL from build_stream_config.yml and its verified HTTP code.

    Returns:
        Dict with keys: host ("" when gitlab_host is not set), address
        (host:port), config_path, url, http_code (0 when not probed or
        unparsable).
    """
    gitlab_config = get_gitlab_config(host)
    gitlab_host = gitlab_config.get("gitlab_host", "")
    gitlab_port = gitlab_config.get("gitlab_https_port", "443")
    probe = {"host": gitlab_host, "address": f"{gitlab_host}:{gitlab_port}",
             "config_path": gitlab_config.get("_config_path", "unknown"),
             "url": "", "http_code": 0}
    if not gitlab_host:
        return probe
    probe["url"] = f"https://{gitlab_host}:{gitlab_port}/"
    try:
        probe["http_code"] = http_status(gitlab_tls(host), probe["url"])
    except RuntimeError:
        probe["http_code"] = 0
    return probe
