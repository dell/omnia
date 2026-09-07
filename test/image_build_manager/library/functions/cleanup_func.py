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

from ._config_helpers import (
    _get_project_name,
    _get_s3_provider,
    _get_shared_path,
)
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
    query_errors = []

    for name in containers:
        cmd = host.run(
            CMDS["podman_ps_check"].format(container=name)
        )
        query_error = None
        if cmd.rc != 0:
            query_error = (
                f"Unable to inspect container '{name}' (rc={cmd.rc})"
            )
            query_errors.append(query_error)
        still_exists = cmd.rc == 0 and name in cmd.stdout
        results.append({
            "container": name,
            "removed": cmd.rc == 0 and not still_exists,
            "query_error": query_error,
            "error": (
                f"Container '{name}' still exists"
                if still_exists else query_error
            ),
        })
        if still_exists or query_error:
            all_removed = False

    return {
        "success": all_removed,
        "results": results,
        "query_errors": query_errors,
        "details": (
            "All containers removed"
            if all_removed else
            "Some containers still exist"
        ),
        "error": None if all_removed else (
            query_errors[0] if query_errors else (
                f"{sum(not item['removed'] for item in results)} "
                "containers remain"
            )
        ),
    }


def check_s3_artifacts_removed(host) -> Dict[str, Any]:
    """Verify managed MinIO storage is removed after the cleanup tag.

    Returns:
        Dict with 'success', 'remaining_buckets', 'details'.
    """
    provider = _get_s3_provider(host)
    if provider == "powerscale":
        return {
            "success": True,
            "skipped": True,
            "provider": provider,
            "storage_path": "external PowerScale S3",
            "remaining_buckets": [],
            "details": (
                "External PowerScale buckets are retained by full cleanup"
            ),
            "error": None,
        }

    storage_path = os.path.join(_get_shared_path(), "s3", "data")
    storage_cmd = host.run(CMDS["dir_exists"].format(path=storage_path))
    if storage_cmd.rc not in (0, 1):
        return {
            "success": False,
            "skipped": False,
            "provider": provider or "minio",
            "storage_path": storage_path,
            "remaining_buckets": [],
            "details": "Unable to inspect managed MinIO storage",
            "error": (
                f"Directory inspection failed with rc={storage_cmd.rc}"
            ),
        }

    storage_exists = storage_cmd.rc == 0 and "exists" in storage_cmd.stdout
    remaining = []
    if storage_exists:
        ls_cmd = host.run(CMDS["s3cmd_ls"])
        if ls_cmd.rc == 0:
            remaining = [
                bucket for bucket in S3_EXPECTED_BUCKETS
                if bucket in ls_cmd.stdout
            ]

    return {
        "success": not storage_exists,
        "skipped": False,
        "provider": provider or "minio",
        "storage_path": storage_path,
        "remaining_buckets": remaining,
        "details": (
            "Managed MinIO storage removed"
            if not storage_exists else
            "Managed MinIO storage still exists"
        ),
        "error": None if not storage_exists else (
            f"Storage directory still exists at {storage_path}"
        ),
    }


def check_s3_images_removed(host) -> Dict[str, Any]:
    """Verify S3 bucket contents are empty after cleanup_images.

    Unlike ``check_s3_artifacts_removed`` (which checks if buckets
    themselves exist after a full cleanup), this checks that the
    *contents* of boot-images are empty — the bucket itself may
    still exist.

    Returns:
        Dict with 'success', 'remaining_objects', 'details'.
    """
    provider = _get_s3_provider(host)
    config_result = host.run(
        CMDS["file_exists"].format(path=S3CMD_CONFIG_PATH)
    )
    storage_path = os.path.join(_get_shared_path(), "s3", "data")
    storage_result = host.run(
        CMDS["dir_exists"].format(path=storage_path)
    )
    if (
        provider != "powerscale"
        and config_result.rc == 1
        and storage_result.rc == 1
    ):
        return {
            "success": True,
            "skipped": True,
            "provider": provider or "minio",
            "remaining_objects": 0,
            "details": (
                "S3 image cleanup is not applicable: managed MinIO "
                "configuration and storage are not initialized"
            ),
            "error": None,
        }

    cmd = host.run(
        CMDS["s3cmd_ls_recursive"].format(bucket="s3://boot-images/")
    )
    if cmd.rc != 0:
        return {
            "success": False,
            "skipped": False,
            "provider": provider or "minio",
            "remaining_objects": 0,
            "details": (
                "Unable to verify s3://boot-images contents: "
                f"s3cmd exited with rc={cmd.rc}"
            ),
        }

    objects = [
        line.strip() for line in cmd.stdout.strip().splitlines()
        if line.strip()
    ]

    return {
        "success": len(objects) == 0,
        "skipped": False,
        "provider": provider or "minio",
        "remaining_objects": len(objects),
        "details": (
            "S3 boot-images bucket is empty"
            if not objects
            else f"S3 still has {len(objects)} object(s)"
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
    query_errors = []

    for svc in SYSTEMD_SERVICES:
        cmd = host.run(
            CMDS["systemctl_is_active"].format(service=svc)
        )
        state = cmd.stdout.strip().lower()
        query_error = None
        if state not in {"active", "inactive", "failed", "unknown"}:
            query_error = (
                f"Unable to determine state for {svc} "
                f"(rc={cmd.rc}, state='{state or 'empty'}')"
            )
            query_errors.append(query_error)
        is_active = state == "active"
        results.append({
            "service": svc,
            "state": state or "unavailable",
            "removed": not is_active and query_error is None,
            "query_error": query_error,
            "error": query_error,
        })
        if is_active or query_error:
            all_inactive = False

    details_lines = []
    for r in results:
        status = "removed" if r["removed"] else f"still {r['state']}"
        details_lines.append(f"  {r['service']}: {status}")

    return {
        "success": all_inactive,
        "results": results,
        "query_errors": query_errors,
        "details": "\n".join(details_lines),
        "error": None if all_inactive else (
            query_errors[0] if query_errors else (
                f"{sum(not item['removed'] for item in results)} "
                "services remain active"
            )
        ),
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
    query_errors = []

    for port in LISTENING_PORTS:
        cmd = host.run(
            CMDS["ss_listen_port"].format(port=port)
        )
        if cmd.rc != 0:
            query_errors.append(
                f"Unable to inspect TCP port {port} (rc={cmd.rc})"
            )
            continue
        if cmd.rc == 0 and str(port) in cmd.stdout:
            still_open.append(port)

    details_lines = []
    for port in LISTENING_PORTS:
        if any(f"port {port} " in error for error in query_errors):
            status = "inspection failed"
        elif port in still_open:
            status = "STILL LISTENING (should be closed)"
        else:
            status = "closed"
        details_lines.append(f"  {port}/tcp: {status}")

    return {
        "success": not still_open and not query_errors,
        "open_ports": still_open,
        "query_errors": query_errors,
        "details": "\n".join(details_lines),
        "error": None if not still_open and not query_errors else (
            query_errors[0] if query_errors else (
                f"{len(still_open)} TCP ports remain open"
            )
        ),
    }


def check_s3cfg_removed(host) -> Dict[str, Any]:
    """Verify s3cmd configuration file is removed after cleanup.

    Returns:
        Dict with 'success', 'details'.
    """
    provider = _get_s3_provider(host)
    if provider == "powerscale":
        return {
            "success": True,
            "skipped": True,
            "provider": provider,
            "path": S3CMD_CONFIG_PATH,
            "details": "PowerScale s3cmd configuration is retained",
            "error": None,
        }

    cmd = host.run(
        CMDS["file_exists"].format(path=S3CMD_CONFIG_PATH)
    )
    if cmd.rc not in (0, 1):
        return {
            "success": False,
            "skipped": False,
            "provider": provider or "minio",
            "path": S3CMD_CONFIG_PATH,
            "details": "Unable to inspect s3cmd configuration",
            "error": f"File inspection failed with rc={cmd.rc}",
        }
    exists = cmd.rc == 0 and "exists" in cmd.stdout

    return {
        "success": not exists,
        "skipped": False,
        "provider": provider or "minio",
        "path": S3CMD_CONFIG_PATH,
        "details": (
            f"{S3CMD_CONFIG_PATH}: removed"
            if not exists
            else f"{S3CMD_CONFIG_PATH}: still exists"
        ),
        "error": None if not exists else "Configuration file still exists",
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
    query_errors = []
    for fpath in files_to_check:
        fname = os.path.basename(fpath)
        cmd = host.run(CMDS["file_exists"].format(path=fpath))
        query_error = None
        if cmd.rc not in (0, 1):
            query_error = (
                f"Unable to inspect credential file '{fname}' "
                f"(rc={cmd.rc})"
            )
            query_errors.append(query_error)
        exists = cmd.rc == 0 and "exists" in cmd.stdout
        results.append({
            "file": fname,
            "path": fpath,
            "removed": not exists and query_error is None,
            "query_error": query_error,
            "error": query_error,
        })
        if exists or query_error:
            all_removed = False

    details_lines = []
    for r in results:
        status = "removed" if r["removed"] else "still exists"
        details_lines.append(f"  {r['file']}: {status}")

    return {
        "success": all_removed,
        "results": results,
        "query_errors": query_errors,
        "details": "\n".join(details_lines),
        "error": None if all_removed else (
            query_errors[0] if query_errors else (
                f"{sum(not item['removed'] for item in results)} "
                "credential files remain"
            )
        ),
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
    if cmd.rc not in (0, 1):
        return {
            "success": False,
            "path": status_path,
            "details": "Unable to inspect build_status.yml",
            "error": f"File inspection failed with rc={cmd.rc}",
        }
    exists = cmd.rc == 0 and "exists" in cmd.stdout

    return {
        "success": not exists,
        "path": status_path,
        "details": (
            "build_status.yml: removed"
            if not exists
            else f"build_status.yml still exists at {status_path}"
        ),
        "error": None if not exists else "build_status.yml still exists",
    }


def check_registry_cleaned(
    host, require_available: bool = False
) -> Dict[str, Any]:
    """Verify registry has no tagged images after cleanup.

    Docker Distribution keeps repository metadata even after all
    manifests are deleted, so ``regctl repo ls`` may still list repo
    names.  This function checks each repo for remaining *tags* —
    a repo with zero tags is considered cleaned.

    Args:
        host: testinfra host object.
        require_available: Fail when the registry cannot be queried. Selective
            cleanup requires the registry to remain available; full cleanup
            permits it to be unavailable.

    Returns:
        Dict with 'success', 'registry_reachable', 'repos',
        'repos_with_tags', 'details'.
    """
    cmd = host.run(
        CMDS["curl_registry_catalog_http"].format(port=REGISTRY_PORT)
    )
    if cmd.rc != 0 or "repositories" not in cmd.stdout:
        storage_path = os.path.join(_get_shared_path(), "registry", "data")
        storage_result = host.run(
            CMDS["dir_exists"].format(path=storage_path)
        )
        service_result = host.run(
            CMDS["systemctl_is_active"].format(service="registry")
        )
        container_result = host.run(
            CMDS["podman_ps_check"].format(container=REGISTRY_CONTAINER)
        )
        managed_state_absent = (
            storage_result.rc == 1
            and service_result.stdout.strip().lower() != "active"
            and container_result.rc == 0
            and REGISTRY_CONTAINER not in container_result.stdout
        )
        if require_available and managed_state_absent:
            return {
                "success": True,
                "skipped": True,
                "registry_reachable": False,
                "repos": [],
                "repos_with_tags": [],
                "query_errors": [],
                "details": (
                    "Registry image cleanup is not applicable: managed "
                    "registry service, container, and storage are not initialized"
                ),
                "error": None,
            }
        details = (
            "Registry not reachable"
            + (
                " but must remain available after cleanup_images"
                if require_available
                else " (expected after full cleanup)"
            )
        )
        return {
            "success": not require_available,
            "skipped": False,
            "registry_reachable": False,
            "repos": [],
            "repos_with_tags": [],
            "query_errors": [],
            "details": details,
            "error": details if require_available else None,
        }

    try:
        data = json.loads(cmd.stdout)
        repos = data.get("repositories", [])
    except (json.JSONDecodeError, ValueError) as exc:
        return {
            "success": False,
            "registry_reachable": True,
            "repos": [],
            "repos_with_tags": [],
            "query_errors": [],
            "details": f"Registry catalog returned invalid JSON: {exc}",
            "error": f"Registry catalog returned invalid JSON: {exc}",
        }

    # Check each repo for remaining tags
    repos_with_tags = []
    query_errors = []
    for repo in repos:
        tags_cmd = host.run(
            CMDS["curl_registry_catalog_http"].format(
                port=REGISTRY_PORT
            ).replace("/v2/_catalog", f"/v2/{repo}/tags/list")
        )
        if tags_cmd.rc != 0:
            query_errors.append(f"{repo}: tag query rc={tags_cmd.rc}")
            continue
        try:
            tag_data = json.loads(tags_cmd.stdout)
        except (json.JSONDecodeError, ValueError) as exc:
            query_errors.append(f"{repo}: invalid tag JSON ({exc})")
            continue
        tags = tag_data.get("tags") or []
        if tags:
            repos_with_tags.append(
                f"{repo} ({len(tags)} tags)"
            )

    return {
        "success": not repos_with_tags and not query_errors,
        "skipped": False,
        "registry_reachable": True,
        "repos": repos,
        "repos_with_tags": repos_with_tags,
        "query_errors": query_errors,
        "error": (
            None
            if not repos_with_tags and not query_errors
            else (
                f"{len(repos_with_tags)} tagged repositories remain"
                if repos_with_tags
                else f"{len(query_errors)} registry tag queries failed"
            )
        ),
        "details": (
            "All registry images deleted (no tagged images remain)"
            if not repos_with_tags and not query_errors
            else "; ".join(filter(None, [
                (
                    "Registry still has tagged repos: "
                    f"{', '.join(repos_with_tags)}"
                    if repos_with_tags else ""
                ),
                (
                    "Registry tag queries failed: "
                    f"{', '.join(query_errors)}"
                    if query_errors else ""
                ),
            ]))
        ),
    }
