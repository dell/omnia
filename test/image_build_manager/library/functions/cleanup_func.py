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

"""Cleanup verification — confirm artifacts are removed after cleanup tag."""

import json
import os
from typing import Dict, Any

from omnia_auto import resolve_domain_input_path

from ._config_helpers import _get_shared_path, _get_project_name
from ..vars.common_vars import (
    DOMAIN_NAME,
    ENV_OMNIA_DATA_PATH,
    ENV_OMNIA_PROJECT_NAME,
    MINIO_CONTAINER,
    REGISTRY_CONTAINER,
    REGISTRY_PORT,
    S3_EXPECTED_BUCKETS,
    S3CMD_CONFIG_PATH,
    CMDS,
    LISTENING_PORTS,
    SYSTEMD_SERVICES,
    CREDENTIALS_FILE_NAME,
    CREDENTIALS_KEY_NAME,
    BUILD_STATUS_PATH,
)


# =============================================================================
# CLEANUP VERIFICATION
# =============================================================================

def check_containers_removed(host) -> Dict[str, Any]:
    """Verify MinIO and registry containers are stopped/removed.

    Returns:
        Dict with 'success', 'results', 'details'.
    """
    containers = [MINIO_CONTAINER, REGISTRY_CONTAINER]
    results = []
    all_removed = True

    for name in containers:
        cmd = host.run(
            CMDS["podman_ps_check"].format(container=name)
        )
        still_exists = cmd.rc == 0 and name in cmd.stdout
        results.append({
            "container": name,
            "removed": not still_exists,
            "error": (
                f"Container '{name}' still exists"
                if still_exists else None
            ),
        })
        if still_exists:
            all_removed = False

    return {
        "success": all_removed,
        "results": results,
        "details": (
            "All containers removed"
            if all_removed else
            "Some containers still exist"
        ),
    }


def check_s3_artifacts_removed(host) -> Dict[str, Any]:
    """Verify S3 buckets/images are cleaned up after cleanup tag.

    Returns:
        Dict with 'success', 'remaining_buckets', 'details'.
    """
    ls_cmd = host.run(CMDS["s3cmd_ls"])
    if ls_cmd.rc != 0:
        return {
            "success": True,
            "remaining_buckets": [],
            "details": "s3cmd not available (expected after cleanup)",
        }

    remaining = []
    for bucket in S3_EXPECTED_BUCKETS:
        if bucket in ls_cmd.stdout:
            remaining.append(bucket)

    return {
        "success": len(remaining) == 0,
        "remaining_buckets": remaining,
        "details": (
            "All S3 buckets cleaned"
            if not remaining else
            f"Remaining buckets: {', '.join(remaining)}"
        ),
    }


# =============================================================================
# CLEANUP VERIFICATION — EXTENDED
# =============================================================================

def check_services_removed(host) -> Dict[str, Any]:
    """Verify MinIO and registry systemd services are inactive/removed.

    Returns:
        Dict with 'success', 'results', 'details'.
    """
    results = []
    all_inactive = True

    for svc in SYSTEMD_SERVICES:
        cmd = host.run(
            CMDS["systemctl_is_active"].format(service=svc)
        )
        state = cmd.stdout.strip() if cmd.rc == 0 else "inactive"
        is_active = state == "active"
        results.append({
            "service": svc,
            "state": state,
            "removed": not is_active,
        })
        if is_active:
            all_inactive = False

    details_lines = []
    for r in results:
        status = "removed" if r["removed"] else f"still {r['state']}"
        details_lines.append(f"  {r['service']}: {status}")

    return {
        "success": all_inactive,
        "results": results,
        "details": "\n".join(details_lines),
    }


def check_firewall_ports_removed(host) -> Dict[str, Any]:
    """Verify service ports are NOT listening after cleanup.

    Checks via ss -tlnp that ports 9000, 9001, 5000 are no longer
    bound. This is more reliable than firewall-cmd since the playbook
    uses container port bindings rather than firewall rules.

    Returns:
        Dict with 'success', 'open_ports', 'details'.
    """
    still_open = []

    for port in LISTENING_PORTS:
        cmd = host.run(
            CMDS["ss_listen_port"].format(port=port)
        )
        if cmd.rc == 0 and str(port) in cmd.stdout:
            still_open.append(port)

    details_lines = []
    for port in LISTENING_PORTS:
        status = (
            "STILL LISTENING (should be closed)"
            if port in still_open else "closed"
        )
        details_lines.append(f"  {port}/tcp: {status}")

    return {
        "success": len(still_open) == 0,
        "open_ports": still_open,
        "details": "\n".join(details_lines),
    }


def check_s3cfg_removed(host) -> Dict[str, Any]:
    """Verify s3cmd configuration file is removed after cleanup.

    Returns:
        Dict with 'success', 'details'.
    """
    cmd = host.run(
        CMDS["file_exists"].format(path=S3CMD_CONFIG_PATH)
    )
    exists = cmd.rc == 0 and "exists" in cmd.stdout

    return {
        "success": not exists,
        "details": (
            f"{S3CMD_CONFIG_PATH}: removed"
            if not exists
            else f"{S3CMD_CONFIG_PATH}: still exists"
        ),
    }


def check_credentials_removed(host) -> Dict[str, Any]:
    """Verify credentials files are removed after cleanup.

    Returns:
        Dict with 'success', 'results', 'details'.
    """
    input_dir = resolve_domain_input_path(
        host, DOMAIN_NAME, ENV_OMNIA_DATA_PATH, ENV_OMNIA_PROJECT_NAME,
    )

    files_to_check = [
        f"{input_dir}/{CREDENTIALS_FILE_NAME}",
        f"{input_dir}/{CREDENTIALS_KEY_NAME}",
    ]

    results = []
    all_removed = True
    for fpath in files_to_check:
        cmd = host.run(CMDS["file_exists"].format(path=fpath))
        exists = cmd.rc == 0 and "exists" in cmd.stdout
        fname = os.path.basename(fpath)
        results.append({
            "file": fname,
            "path": fpath,
            "removed": not exists,
        })
        if exists:
            all_removed = False

    details_lines = []
    for r in results:
        status = "removed" if r["removed"] else "still exists"
        details_lines.append(f"  {r['file']}: {status}")

    return {
        "success": all_removed,
        "results": results,
        "details": "\n".join(details_lines),
    }


def check_build_output_removed(host) -> Dict[str, Any]:
    """Verify build_status.yml is removed after cleanup.

    Returns:
        Dict with 'success', 'details'.
    """
    shared = _get_shared_path()
    project = _get_project_name()
    status_path = BUILD_STATUS_PATH.format(
        shared_path=shared, project=project
    )

    cmd = host.run(CMDS["file_exists"].format(path=status_path))
    exists = cmd.rc == 0 and "exists" in cmd.stdout

    return {
        "success": not exists,
        "details": (
            "build_status.yml: removed"
            if not exists
            else f"build_status.yml still exists at {status_path}"
        ),
    }


def check_registry_cleaned(host) -> Dict[str, Any]:
    """Verify registry has no images after cleanup.

    Returns:
        Dict with 'success', 'registry_reachable', 'repos', 'details'.
    """
    cmd = host.run(
        CMDS["curl_registry_catalog_http"].format(port=REGISTRY_PORT)
    )
    if cmd.rc != 0 or "repositories" not in cmd.stdout:
        return {
            "success": True,
            "registry_reachable": False,
            "repos": [],
            "details": (
                "Registry not reachable (expected after cleanup)"
            ),
        }

    try:
        data = json.loads(cmd.stdout)
        repos = data.get("repositories", [])
    except (json.JSONDecodeError, ValueError):
        repos = []

    return {
        "success": len(repos) == 0,
        "registry_reachable": True,
        "repos": repos,
        "details": (
            "Registry empty (no images)"
            if not repos
            else f"Registry still has {len(repos)} repos: "
                 f"{', '.join(repos)}"
        ),
    }
