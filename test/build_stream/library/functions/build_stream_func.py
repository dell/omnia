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
Build Stream — BuildStream Health Verification Functions.

Functions to verify BSM API health, database tables,
playbook paths, venv, TLS certs, and watcher service.
"""

import json
from typing import Any, Dict

from omnia_auto import load_test_config, run_on_host

from library.vars.common_vars import (
    BSM_HEALTH_PATH,
    BSM_HOST_IP_KEY,
    BSM_PORT_KEY,
    BUILD_STREAM_CONFIG_FILE,
    CMDS,
    EXPECTED_PLAYBOOK_ENTRIES,
    EXPECTED_TABLES,
    NFS_QUEUE_DIR_DEFAULT,
    OMNIA_VENV_PATH_DEFAULT,
    PLAYBOOK_PATHS_YML,
    POSTGRES_CONTAINER_NAME,
    POSTGRES_DB_NAME,
    POSTGRES_USER,
)


def _get_bsm_config_path() -> str:
    """Return the resolved path to build_stream_config.yml on the target host."""
    config = load_test_config()
    project = config.get("project_name", "project_default")
    data_path = config.get("shared_path", "/opt/omnia/build_stream")
    return (
        f"{data_path}/input/{project}/"
        f"{BUILD_STREAM_CONFIG_FILE}"
    )


def _get_bsm_config_value(host, key: str) -> str:
    """Read a value from build_stream_config.yml on the target host.

    Args:
        host: Testinfra host connection.
        key: YAML key to extract.

    Returns:
        Value string, or empty string if not found.
    """
    config_path = _get_bsm_config_path()
    cmd = CMDS["cat_file"].format(path=config_path)
    result = run_on_host(host, cmd)
    if result.rc != 0 or not result.stdout.strip():
        return ""
    for line in result.stdout.strip().split("\n"):
        if key in line and ":" in line:
            return line.split(":", 1)[1].strip().strip('"').strip("'")
    return ""


def check_build_stream_enabled(host) -> Dict[str, Any]:
    """Check if build_stream is enabled in build_stream_config.yml.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, details, error.
    """
    config_path = _get_bsm_config_path()
    value = _get_bsm_config_value(host, "enable_build_stream")
    if not value:
        return {
            "success": False,
            "details": "",
            "error": (
                f"enable_build_stream key not found or config file missing. "
                f"Checked: {config_path}"
            ),
        }
    enabled = value.lower() in ("true", "yes", "1")
    if enabled:
        return {
            "success": True,
            "details": f"enable_build_stream: true (from {config_path})",
            "error": "",
        }
    return {
        "success": False,
        "details": f"enable_build_stream: {value}",
        "error": (
            f"enable_build_stream={value} in {config_path}. "
            f"Set to 'true' to enable."
        ),
    }


def check_build_stream_health(host) -> Dict[str, Any]:
    """Verify the BSM API /health endpoint returns healthy.

    Reads host_ip and port from build_stream_config.yml,
    then runs curl on the OIM host.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, status, url, details, error.
    """
    result = {
        "success": False,
        "status": "",
        "url": "",
        "details": "",
        "error": "",
    }

    config_path = _get_bsm_config_path()
    host_ip = _get_bsm_config_value(host, BSM_HOST_IP_KEY)
    port = _get_bsm_config_value(host, BSM_PORT_KEY)

    if not host_ip:
        result["error"] = (
            f"{BSM_HOST_IP_KEY} not found or empty in {config_path}. "
            f"Set the BSM host IP in build_stream_config.yml."
        )
        return result
    if not port:
        result["error"] = (
            f"{BSM_PORT_KEY} not found or empty in {config_path}. "
            f"Set the BSM port in build_stream_config.yml."
        )
        return result

    url = f"https://{host_ip}:{port}{BSM_HEALTH_PATH}"
    result["url"] = url

    http_cmd = CMDS["curl_health"].format(
        host=host_ip, port=port, path=BSM_HEALTH_PATH,
    )
    http_result = run_on_host(host, http_cmd)
    http_code = http_result.stdout.strip()

    if http_result.rc == 0 and http_code == "200":
        body_cmd = CMDS["curl_health_body"].format(
            host=host_ip, port=port, path=BSM_HEALTH_PATH,
        )
        body_result = run_on_host(host, body_cmd)
        body = body_result.stdout.strip()

        if '"healthy"' in body.replace(" ", ""):
            result["success"] = True
            result["status"] = "healthy"
            result["details"] = f"GET {url} -> {body}"
            return result

        result["status"] = "unhealthy"
        result["error"] = f"Unexpected response body: {body}"
        return result

    result["status"] = "unreachable"
    result["error"] = (
        f"GET {url} unreachable. HTTP: {http_code or 'N/A'} "
        f"(curl rc={http_result.rc})"
    )
    return result


def check_postgres_tables(host) -> Dict[str, Any]:
    """Verify all expected tables exist in build_stream_db.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, found, missing, details, error.
    """
    result = {
        "success": False,
        "found": [],
        "missing": [],
        "details": "",
        "error": "",
    }

    cmd = CMDS["psql_list_tables"].format(
        container=POSTGRES_CONTAINER_NAME,
        user=POSTGRES_USER,
        db=POSTGRES_DB_NAME,
    )
    cmd_result = run_on_host(host, cmd)

    if cmd_result.rc != 0:
        stderr = cmd_result.stderr.strip() if cmd_result.stderr else ""
        result["error"] = (
            f"psql query failed (rc={cmd_result.rc}). "
            f"Container '{POSTGRES_CONTAINER_NAME}' may not be running. "
            f"Check: podman ps --filter name={POSTGRES_CONTAINER_NAME}"
            + (f" | stderr: {stderr}" if stderr else "")
        )
        return result

    tables = [
        line.strip()
        for line in cmd_result.stdout.strip().split("\n")
        if line.strip()
    ]

    for table in EXPECTED_TABLES:
        if table in tables:
            result["found"].append(table)
        else:
            result["missing"].append(table)

    result["success"] = len(result["missing"]) == 0
    result["details"] = (
        f"{len(result['found'])}/{len(EXPECTED_TABLES)} tables found"
    )
    return result


def check_playbook_paths_yml(host) -> Dict[str, Any]:
    """Verify playbook_paths.yml exists and contains expected entries.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, found, missing, details, error.
    """
    result = {
        "success": False,
        "found": [],
        "missing": [],
        "details": "",
        "error": "",
    }

    config = load_test_config()
    clone_path = config.get("clone_path", "/root/omnia")
    full_path = f"{clone_path}/{PLAYBOOK_PATHS_YML}"

    cat_cmd = CMDS["cat_file"].format(path=full_path)
    cat_result = run_on_host(host, cat_cmd)

    if cat_result.rc != 0 or not cat_result.stdout.strip():
        result["error"] = f"playbook_paths.yml not found at {full_path}"
        return result

    content = cat_result.stdout.strip()
    for entry in EXPECTED_PLAYBOOK_ENTRIES:
        if entry in content:
            result["found"].append(entry)
        else:
            result["missing"].append(entry)

    result["success"] = len(result["missing"]) == 0
    result["details"] = (
        f"Entries found: {', '.join(result['found'])}"
    )
    return result


def check_playbook_paths_resolvable(host) -> Dict[str, Any]:
    """Verify all paths in playbook_paths.yml resolve to existing files.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, resolved, unresolved, details, error.
    """
    result = {
        "success": False,
        "resolved": [],
        "unresolved": [],
        "details": "",
        "error": "",
    }

    config = load_test_config()
    clone_path = config.get("clone_path", "/root/omnia")
    full_path = f"{clone_path}/{PLAYBOOK_PATHS_YML}"

    cmd = (
        f"python3 -c \""
        f"import yaml; data=yaml.safe_load(open('{full_path}'));"
        f"paths=data.get('playbook_paths',{{}});"
        f"[print(v) for v in paths.values()]"
        f"\" 2>/dev/null"
    )
    cmd_result = run_on_host(host, cmd)

    if cmd_result.rc != 0:
        result["error"] = "Failed to parse playbook_paths.yml"
        return result

    paths = [
        p.strip() for p in cmd_result.stdout.strip().split("\n")
        if p.strip()
    ]

    for playbook_path in paths:
        if not playbook_path.startswith("/"):
            playbook_path = f"{clone_path}/{playbook_path}"
        check_cmd = CMDS["file_exists"].format(path=playbook_path)
        check_result = run_on_host(host, check_cmd)
        if check_result.stdout.strip() == "exists":
            result["resolved"].append(playbook_path)
        else:
            result["unresolved"].append(playbook_path)

    result["success"] = len(result["unresolved"]) == 0
    result["details"] = (
        f"{len(result['resolved'])}/{len(paths)} paths resolved"
    )
    return result


def check_omnia_venv(host) -> Dict[str, Any]:
    """Verify the shared Python venv exists with ansible-playbook.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, details, error.
    """
    venv_path = OMNIA_VENV_PATH_DEFAULT
    cmd = CMDS["venv_ansible_playbook"].format(venv_path=venv_path)
    cmd_result = run_on_host(host, cmd)

    if cmd_result.stdout.strip() == "exists":
        return {
            "success": True,
            "details": f"ansible-playbook found in {venv_path}",
            "error": "",
        }
    return {
        "success": False,
        "details": "",
        "error": f"ansible-playbook not found in {venv_path}/bin/",
    }


def check_bsm_tls_certificate(host) -> Dict[str, Any]:
    """Verify BSM TLS certificate is valid X.509 PEM.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, details, error.
    """
    from library.vars.common_vars import BSM_TLS_CERT_PATH

    cert_path = BSM_TLS_CERT_PATH
    cmd = CMDS["openssl_verify_cert"].format(cert_path=cert_path)
    cmd_result = run_on_host(host, cmd)

    if cmd_result.rc == 0 and cmd_result.stdout.strip():
        return {
            "success": True,
            "details": cmd_result.stdout.strip(),
            "error": "",
        }
    return {
        "success": False,
        "details": "",
        "error": f"TLS certificate invalid or missing at {cert_path}",
    }


def check_nfs_queue_directory(host) -> Dict[str, Any]:
    """Verify NFS queue directory is accessible and writable.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, path, details, error.
    """
    queue_dir = NFS_QUEUE_DIR_DEFAULT
    cmd = CMDS["dir_exists"].format(path=queue_dir)
    cmd_result = run_on_host(host, cmd)

    if cmd_result.stdout.strip() == "exists":
        return {
            "success": True,
            "path": queue_dir,
            "details": f"NFS queue directory exists: {queue_dir}",
            "error": "",
        }
    return {
        "success": False,
        "path": queue_dir,
        "details": "",
        "error": f"NFS queue directory not found: {queue_dir}",
    }


def check_playbook_watcher(host) -> Dict[str, Any]:
    """Verify playbook watcher service is running.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: success, details, error.
    """
    cmd = CMDS["systemctl_is_active"].format(
        service="playbook-watcher.service",
    )
    cmd_result = run_on_host(host, cmd)
    status = cmd_result.stdout.strip()

    if status == "active":
        return {
            "success": True,
            "details": "playbook-watcher.service: active",
            "error": "",
        }
    return {
        "success": False,
        "details": f"playbook-watcher.service: {status}",
        "error": f"Watcher not active, status: {status}",
    }
