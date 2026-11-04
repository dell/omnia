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
Build Stream — Cleanup Verification Functions.

Functions to verify GitLab cleanup and BuildStream domain cleanup.
Checks that containers, services, directories, credentials, and
volumes are properly removed after running cleanup playbooks.
"""

from typing import Any, Dict, List

from omnia_auto import read_remote_yaml

from library.cleanup_inspection import (
    PATH_ABSENT,
    PATH_EXISTS,
    classify_path_probe,
    is_expected_disabled_state,
    is_expected_stopped_state,
)
# GitLab cleanup checks live in gitlab_cleanup_func; they are re-exported
# here so existing ``cleanup_func`` imports keep working.
from library.functions.gitlab_cleanup_func import (
    check_gitlab_directories_removed,
    check_gitlab_packages_removed,
    check_gitlab_port_free,
    check_gitlab_runner_container_removed,
    check_gitlab_runner_quadlet_removed,
    check_gitlab_runner_services_stopped,
    check_gitlab_services_stopped,
    check_gitlab_url_not_accessible,
)
from library.functions.probe_func import Probe, port_closed, run_cmd, summarize_probes
from library.vars.common_vars import (
    BSM_CONTAINER_NAME,
    BSM_PORT_KEY,
    BUILD_STREAM_CONFIG_FILE,
    BUILDSTREAM_CLEANUP_DIRECTORIES,
    BUILDSTREAM_HOST_LOG_DIRECTORY,
    BUILDSTREAM_WATCHER_SOURCE,
    PLAYBOOK_WATCHER_SERVICE_FILE,
    PLAYBOOK_WATCHER_SERVICE_NAME,
    POSTGRES_CONTAINER_NAME,
    POSTGRES_DATA_DIR,
    QUADLET_DIR,
)

from ._config_helpers import (
    resolve_build_stream_data_path,
    resolve_build_stream_input_path,
)

__all__ = [
    "check_buildstream_api_port_closed",
    "check_buildstream_container_removed",
    "check_buildstream_container_stopped",
    "check_buildstream_directories_removed",
    "check_buildstream_quadlet_files_removed",
    "check_buildstream_runtime_caches_removed",
    "check_buildstream_services_stopped",
    "check_credentials_per_flag",
    "check_gitlab_directories_removed",
    "check_gitlab_packages_removed",
    "check_gitlab_port_free",
    "check_gitlab_runner_container_removed",
    "check_gitlab_runner_quadlet_removed",
    "check_gitlab_runner_services_stopped",
    "check_gitlab_services_stopped",
    "check_gitlab_url_not_accessible",
    "check_playbook_watcher_service_disabled",
    "check_playbook_watcher_service_file_removed",
    "check_playbook_watcher_service_stopped",
    "check_postgres_container_removed",
    "check_postgres_container_stopped",
    "check_postgres_data_per_backup",
    "check_postgres_quadlet_files_removed",
    "check_postgres_services_stopped",
]


# =========================================================================
# SECTION C.1: BuildStream Domain Cleanup Verification
# =========================================================================

def container_probes(host, container: str, removed: bool) -> List[Probe]:
    """Probe that ``container`` is not running (and, when ``removed``, absent)."""
    listing = run_cmd(host, "podman_ps_all", container=container)
    if listing.rc != 0:
        return [(f"Container {container}", f"INSPECTION FAILED (rc={listing.rc})", False)]
    status = listing.stdout.strip().partition(" ")[2]
    if not status:
        return [(f"Container {container}", "removed", True)]
    running = status.startswith("Up")
    if removed:
        return [(f"Container {container}", f"STILL EXISTS ({status})", False)]
    return [(f"Container {container}", f"STILL RUNNING ({status})" if running
             else f"stopped ({status})", not running)]


def _quadlet_probes(host, container: str) -> List[Probe]:
    """Probe that the quadlet unit of ``container`` and every related file are gone."""
    expected = f"{QUADLET_DIR}/{container}.container"
    found = run_cmd(host, "quadlet_files", dir=QUADLET_DIR, pattern=f"{container}*")
    if found.rc != 0:
        return [(f"Quadlet files {QUADLET_DIR}/{container}*",
                 f"INSPECTION FAILED (rc={found.rc})", False)]
    paths = sorted({expected, *found.stdout.split()})
    remaining = set(found.stdout.split())
    return [(f"Quadlet {path}", "STILL EXISTS" if path in remaining else "removed",
             path not in remaining) for path in paths]


def unit_stopped(host, unit: str) -> Probe:
    """Probe that systemd reports ``unit`` stopped or unknown (unit file removed)."""
    state = run_cmd(host, "systemctl_is_active", service=unit)
    status = state.stdout.strip() or "unknown"
    if status == "active":
        return f"Unit {unit}", "STILL ACTIVE", False
    if is_expected_stopped_state(state.rc, status):
        return f"Unit {unit}", status, True
    return f"Unit {unit}", f"INSPECTION FAILED (rc={state.rc}, status={status})", False


def _service_probes(host, container: str) -> List[Probe]:
    """Probe every systemd service of ``container`` (the quadlet one and any other)."""
    listing = run_cmd(host, "service_units", pattern=f"{container}*")
    units = {line.split()[0] for line in listing.stdout.splitlines() if line.strip()}
    return [unit_stopped(host, unit) for unit in sorted({f"{container}.service", *units})]


def directory_removed(host, path: str) -> Probe:
    """Probe that the directory ``path`` was removed."""
    probe = run_cmd(host, "dir_exists", path=path)
    state = classify_path_probe(probe.rc, probe.stdout)
    if state == PATH_EXISTS:
        return f"Directory {path}", "STILL EXISTS", False
    if state == PATH_ABSENT:
        return f"Directory {path}", "removed", True
    return f"Directory {path}", f"INSPECTION FAILED (rc={probe.rc})", False


def check_buildstream_container_stopped(host) -> Dict[str, Any]:
    """Verify the omnia_build_stream container is not running.

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    return summarize_probes("bsm_container", container_probes(host, BSM_CONTAINER_NAME, False))


def check_buildstream_container_removed(host) -> Dict[str, Any]:
    """Verify the omnia_build_stream container is removed.

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    return summarize_probes("bsm_container", container_probes(host, BSM_CONTAINER_NAME, True))


def check_buildstream_quadlet_files_removed(host) -> Dict[str, Any]:
    """Verify every omnia_build_stream quadlet file is removed (one line per file).

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    return summarize_probes("bsm_quadlets", _quadlet_probes(host, BSM_CONTAINER_NAME))


def check_buildstream_services_stopped(host) -> Dict[str, Any]:
    """Verify every omnia_build_stream systemd service is stopped (one line per unit).

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    return summarize_probes("bsm_services", _service_probes(host, BSM_CONTAINER_NAME))


def check_playbook_watcher_service_stopped(host) -> Dict[str, Any]:
    """Verify playbook-watcher.service is stopped.

    systemctl reports ``inactive`` (rc 3) while the unit file exists and
    ``inactive``/``unknown`` (rc 4) once cleanup removed it; both pass.

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    return summarize_probes("watcher", [unit_stopped(host, PLAYBOOK_WATCHER_SERVICE_NAME)])


def check_playbook_watcher_service_disabled(host) -> Dict[str, Any]:
    """Verify playbook-watcher.service is no longer enabled at boot.

    ``systemctl is-enabled`` reports ``disabled`` (rc 1) while the unit file
    exists and ``not-found`` (rc 1 or 4, by systemd version) once cleanup
    removed it; both pass. ``enabled`` fails.

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    state = run_cmd(host, "systemctl_is_enabled", service=PLAYBOOK_WATCHER_SERVICE_NAME)
    status = state.stdout.strip() or "unknown"
    label = f"Unit {PLAYBOOK_WATCHER_SERVICE_NAME}"
    if status == "enabled":
        probe = (label, "STILL ENABLED", False)
    elif is_expected_disabled_state(state.rc, status):
        probe = (label, status, True)
    else:
        probe = (label, f"INSPECTION FAILED (rc={state.rc}, status={status})", False)
    return summarize_probes("watcher_disabled", [probe])


def check_playbook_watcher_service_file_removed(host) -> Dict[str, Any]:
    """Verify the playbook-watcher.service unit file is removed.

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    probe = run_cmd(host, "file_exists", path=PLAYBOOK_WATCHER_SERVICE_FILE)
    state = classify_path_probe(probe.rc, probe.stdout)
    status = {PATH_EXISTS: "STILL EXISTS", PATH_ABSENT: "removed"}.get(
        state, f"INSPECTION FAILED (rc={probe.rc})")
    return summarize_probes("watcher_unit_file", [
        (f"Unit file {PLAYBOOK_WATCHER_SERVICE_FILE}", status, state == PATH_ABSENT)])


def check_postgres_container_stopped(host) -> Dict[str, Any]:
    """Verify the omnia_postgres container is not running.

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    return summarize_probes("postgres_container",
                            container_probes(host, POSTGRES_CONTAINER_NAME, False))


def check_postgres_container_removed(host) -> Dict[str, Any]:
    """Verify the omnia_postgres container is removed.

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    return summarize_probes("postgres_container",
                            container_probes(host, POSTGRES_CONTAINER_NAME, True))


def check_postgres_quadlet_files_removed(host) -> Dict[str, Any]:
    """Verify every omnia_postgres quadlet file is removed (one line per file).

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    return summarize_probes("postgres_quadlets", _quadlet_probes(host, POSTGRES_CONTAINER_NAME))


def check_postgres_services_stopped(host) -> Dict[str, Any]:
    """Verify every omnia_postgres systemd service is stopped (one line per unit).

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    return summarize_probes("postgres_services", _service_probes(host, POSTGRES_CONTAINER_NAME))


def check_buildstream_directories_removed(host) -> Dict[str, Any]:
    """Verify every BuildStream runtime directory is removed (one line per directory).

    The list matches build_stream_cleanup_directory and
    build_stream_host_log_directory of the cleanup_build_stream role.

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    omnia_path = resolve_build_stream_data_path(host).rsplit("/build_stream", 1)[0]
    directories = [f"{omnia_path}/{name}" for name in BUILDSTREAM_CLEANUP_DIRECTORIES]
    directories.append(BUILDSTREAM_HOST_LOG_DIRECTORY)
    return summarize_probes("bsm_directories", [directory_removed(host, path) for path in directories])


def check_buildstream_runtime_caches_removed(host) -> Dict[str, Any]:
    """Verify the runtime source and input remain while Python caches are removed.

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    data_path = resolve_build_stream_data_path(host)
    input_dir = resolve_build_stream_input_path(host)
    root_present = _path_state(host, data_path)
    probes = [(f"Runtime root {data_path}", "preserved" if root_present else "REMOVED",
               root_present)]
    for path in (f"{data_path}/{BUILDSTREAM_WATCHER_SOURCE}",
                 f"{input_dir}/{BUILD_STREAM_CONFIG_FILE}"):
        present = _path_state(host, path)
        probes.append((f"File {path}", "preserved" if present else "MISSING", present))
    found = run_cmd(host, "python_caches", path=data_path)
    remaining = [line.strip() for line in found.stdout.splitlines() if line.strip()]
    if found.rc != 0:
        probes.append((f"Python caches under {data_path}",
                       f"INSPECTION FAILED (rc={found.rc})", False))
    elif not remaining:
        probes.append((f"Python caches under {data_path}", "none left", True))
    probes.extend((f"Python cache {path}", "STILL EXISTS", False) for path in remaining)
    return summarize_probes("bsm_runtime_caches", probes)


def _path_state(host, path: str) -> bool:
    """Return whether a file or directory exists on the OIM."""
    return run_cmd(host, "path_exists", path=path).rc == 0


def check_postgres_data_per_backup(host, postgres_backup: bool) -> Dict[str, Any]:
    """Verify the Postgres data follows ``-e postgres_backup=<flag>``.

    cleanup_postgres.yml keeps ``<OMNIA_DATA_PATH>/build_stream/postgres`` and the
    omnia_postgres podman volumes when postgres_backup is true and deletes
    both when it is false.

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    omnia_path = resolve_build_stream_data_path(host).rsplit("/build_stream", 1)[0]
    data_dir = f"{omnia_path}/{POSTGRES_DATA_DIR}"
    volumes = [name for name in run_cmd(host, "podman_volume_names").stdout.split()
               if POSTGRES_CONTAINER_NAME in name]
    present = _path_state(host, data_dir)
    if postgres_backup:
        probes = [(f"postgres_backup=true: {data_dir}", "preserved" if present else "DELETED",
                   present)]
    else:
        probes = [
            (f"postgres_backup=false: {data_dir}", "STILL EXISTS" if present else "deleted",
             not present),
            (f"postgres_backup=false: {POSTGRES_CONTAINER_NAME} volumes",
             f"STILL EXIST: {', '.join(volumes)}" if volumes else "deleted", not volumes),
        ]
    return summarize_probes("postgres_data", probes)


def check_credentials_per_flag(host, files, cleanup_credentials: bool) -> Dict[str, Any]:
    """Verify credential files follow ``-e cleanup_credentials=<flag>``.

    true: every file is deleted. false: every file is kept.

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    input_dir = resolve_build_stream_input_path(host)
    probes = []
    for name in files:
        path = f"{input_dir}/{name}"
        present = _path_state(host, path)
        if cleanup_credentials:
            probes.append((f"cleanup_credentials=true: {path}",
                           "STILL EXISTS" if present else "deleted", not present))
        else:
            probes.append((f"cleanup_credentials=false: {path}",
                           "kept" if present else "DELETED", present))
    return summarize_probes("credentials", probes)


def check_buildstream_api_port_closed(host) -> Dict[str, Any]:
    """Verify nothing listens on the BuildStream API port after cleanup.

    The port is read from build_stream_config.yml, which cleanup keeps.

    Args:
        host: Testinfra host connection.

    Returns:
        Dict with keys: name, success, fields, failures, error.
    """
    config_path = f"{resolve_build_stream_input_path(host)}/{BUILD_STREAM_CONFIG_FILE}"
    try:
        port = (read_remote_yaml(host, config_path) or {}).get(BSM_PORT_KEY)
    except (OSError, RuntimeError, ValueError) as exc:
        return summarize_probes("api_port", [(BSM_PORT_KEY, f"UNREADABLE ({exc})", False)])
    if not port:
        return summarize_probes(
            "api_port", [(f"{BSM_PORT_KEY} in {config_path}", "NOT SET", False)])
    return summarize_probes("api_port", [
        (f"{BSM_PORT_KEY} in {config_path}", str(port), True),
        port_closed(host, int(port)),
    ])
