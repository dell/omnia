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

"""Postcondition helpers for the supported full Orchestrator cleanup."""

import os
from typing import Any

import yaml
from omnia_auto import load_test_config, run_on_host

from ..vars.cleanup_vars import (
    CLEANUP_EXTRA_VARIABLES,
    CREDENTIAL_FILES,
    OPENCHAMI_CLEANUP_CONTAINERS,
    OPENCHAMI_CLEANUP_PACKAGES,
    OPENCHAMI_CLEANUP_UNITS,
    OPENCHAMI_CLEANUP_VOLUMES,
    OPENCHAMI_STATIC_PATHS,
    OPENLDAP_CONTAINER,
    OPENLDAP_QUADLET,
    OPENLDAP_SERVICE,
    PRESERVED_INPUT_FILES,
)
from .project_func import (
    resolve_target_input_project_path,
    resolve_target_omnia_data_path,
    resolve_target_output_project_path,
    resolve_target_shared_path,
)


def _result(
    success: bool,
    summary: str,
    fields: list[tuple[str, object]],
    error: str = "",
) -> dict[str, Any]:
    """Build one structured cleanup result."""
    return {
        "success": success,
        "details": summary,
        "fields": fields,
        "error": error,
    }


def cleanup_extra_vars(config: dict[str, Any] | None = None) -> dict[str, str]:
    """Return deterministic supported full-cleanup extra variables."""
    source = dict(config if config is not None else load_test_config())
    selected: dict[str, str] = {}
    for name in CLEANUP_EXTRA_VARIABLES:
        value = source.get(name, True)
        if not isinstance(value, bool):
            raise TypeError(f"{name} must be true or false")
        selected[name] = "true" if value else "false"
    return selected


def cleanup_selection_fields(
    config: dict[str, Any] | None = None,
) -> list[tuple[str, str]]:
    """Describe the effective product behavior selected for cleanup."""
    source = dict(config if config is not None else load_test_config())

    def _choice(name: str, enabled: str, disabled: str) -> str:
        return enabled if source.get(name, True) else disabled

    return [
        (
            "Credentials",
            _choice(
                "cleanup_credentials",
                "remove",
                "preserve",
            ),
        ),
        (
            "Slurm shared data",
            _choice(
                "cleanup_slurm",
                "delete",
                "preserve",
            ),
        ),
        (
            "Kubernetes shared data",
            _choice(
                "cleanup_k8s",
                "delete",
                "preserve",
            ),
        ),
    ]


def _command_absent(host, command: str, name: str) -> tuple[str, bool]:
    """Return a readable absent state for a command with 0/1 existence RCs."""
    probe = run_on_host(host, command, name)
    if probe.rc == 1:
        return "removed", True
    if probe.rc == 0:
        return "STILL EXISTS", False
    return f"inspection failed (rc={probe.rc})", False


def check_cleanup_openchami(host) -> dict[str, Any]:
    """Verify full cleanup removed OpenCHAMI runtime and persistent state."""
    fields: list[tuple[str, object]] = []
    failures: list[str] = []

    for unit in OPENCHAMI_CLEANUP_UNITS:
        probe = run_on_host(host, "systemctl is-active %s", unit)
        state = probe.stdout.strip() or "inactive"
        okay = state != "active"
        fields.append((f"Unit {unit}", state))
        if not okay:
            failures.append(f"active unit: {unit}")

    for container in OPENCHAMI_CLEANUP_CONTAINERS:
        state, okay = _command_absent(host, "podman container exists %s", container)
        fields.append((f"Container {container}", state))
        if not okay:
            failures.append(f"container: {container}")

    for volume in OPENCHAMI_CLEANUP_VOLUMES:
        state, okay = _command_absent(host, "podman volume exists %s", volume)
        fields.append((f"Volume {volume}", state))
        if not okay:
            failures.append(f"volume: {volume}")

    for package in OPENCHAMI_CLEANUP_PACKAGES:
        state, okay = _command_absent(host, "rpm -q %s", package)
        fields.append((f"Package {package}", state))
        if not okay:
            failures.append(f"package: {package}")

    omnia_data = resolve_target_omnia_data_path(host)
    shared_path = resolve_target_shared_path(host)
    paths = [
        *OPENCHAMI_STATIC_PATHS,
        os.path.join(omnia_data, "openchami", "workdir"),
        os.path.join(omnia_data, "openchami", "inventory"),
        os.path.join(shared_path, "log", "openchami"),
    ]
    for path in paths:
        absent = not host.file(path).exists
        fields.append((path, "removed" if absent else "STILL EXISTS"))
        if not absent:
            failures.append(f"path: {path}")

    attributes = run_on_host(host, "lsattr -d %s", "/etc/resolv.conf")
    immutable = attributes.rc == 0 and "i" in attributes.stdout.split(maxsplit=1)[0]
    fields.append(("/etc/resolv.conf immutable", "no" if not immutable else "YES"))
    if immutable:
        failures.append("immutable /etc/resolv.conf")

    return _result(
        not failures,
        "OpenCHAMI runtime, packages, volumes and generated state checked",
        fields,
        "; ".join(failures),
    )


def check_cleanup_openldap(host) -> dict[str, Any]:
    """Verify full cleanup removed the OpenLDAP proxy deployment."""
    fields: list[tuple[str, object]] = []
    failures: list[str] = []

    service = run_on_host(host, "systemctl is-active %s", OPENLDAP_SERVICE)
    service_state = service.stdout.strip() or "inactive"
    fields.append((f"Unit {OPENLDAP_SERVICE}", service_state))
    if service_state == "active":
        failures.append(f"active unit: {OPENLDAP_SERVICE}")

    state, absent = _command_absent(
        host, "podman container exists %s", OPENLDAP_CONTAINER
    )
    fields.append((f"Container {OPENLDAP_CONTAINER}", state))
    if not absent:
        failures.append(f"container: {OPENLDAP_CONTAINER}")

    auth_path = os.path.join(resolve_target_omnia_data_path(host), "auth")
    for path in (OPENLDAP_QUADLET, auth_path):
        removed = not host.file(path).exists
        fields.append((path, "removed" if removed else "STILL EXISTS"))
        if not removed:
            failures.append(f"path: {path}")

    return _result(
        not failures,
        "OpenLDAP service, container, Quadlet and data checked",
        fields,
        "; ".join(failures),
    )


def _read_yaml(host, path: str) -> dict[str, Any]:
    """Read one required target YAML mapping."""
    remote = host.file(path)
    if not remote.is_file:
        raise ValueError(f"Required cleanup input is missing: {path}")
    content = yaml.safe_load(remote.content_string) or {}
    if not isinstance(content, dict):
        raise TypeError(f"Expected a YAML mapping in {path}")
    return content


def _referenced_storage_names(omnia_config: dict[str, Any], component: str) -> set[str]:
    """Return storage names handled for one full-cleanup component."""
    names: set[str] = set()
    if component == "slurm":
        for cluster in omnia_config.get("slurm_cluster", []) or []:
            if not isinstance(cluster, dict):
                continue
            for key in ("nfs_storage_name", "vast_storage_name"):
                value = cluster.get(key)
                if isinstance(value, str) and value.strip():
                    names.add(value.strip())
    elif component == "kubernetes":
        for cluster in omnia_config.get("service_k8s_cluster", []) or []:
            if not isinstance(cluster, dict):
                continue
            value = cluster.get("nfs_storage_name")
            if isinstance(value, str) and value.strip():
                names.add(value.strip())
    else:
        raise ValueError(f"Unsupported cleanup storage component: {component}")
    return names


def _check_cleanup_storage(host, component: str) -> dict[str, Any]:
    """Verify one component's configured storage cleanup policy and state."""
    input_path = resolve_target_input_project_path(host)
    try:
        omnia_config = _read_yaml(host, os.path.join(input_path, "omnia_config.yml"))
        storage_config = _read_yaml(
            host, os.path.join(input_path, "storage_config.yml")
        )
    except (OSError, TypeError, ValueError, yaml.YAMLError) as exc:
        return _result(False, "Unable to resolve cleanup storage", [], str(exc))

    names = _referenced_storage_names(omnia_config, component)
    mounts = storage_config.get("mounts", []) or []
    if not isinstance(mounts, list):
        return _result(
            False,
            "Unable to resolve cleanup storage",
            [],
            "storage_config.yml mounts must be a list",
        )

    fields: list[tuple[str, object]] = []
    failures: list[str] = []
    resolved: set[str] = set()
    delete_requested = load_test_config().get(
        f"cleanup_{'k8s' if component == 'kubernetes' else component}", True
    )
    fields.append(
        (
            "Shared-data policy",
            "delete" if delete_requested else "preserve",
        )
    )
    for mount in mounts:
        if not isinstance(mount, dict) or mount.get("name") not in names:
            continue
        name = str(mount.get("name"))
        path = mount.get("mount_point")
        if not isinstance(path, str) or not path.startswith("/"):
            failures.append(f"{name}: invalid mount_point")
            continue
        resolved.add(name)
        mounted = run_on_host(host, "findmnt -rn -M %s", path).rc == 0
        in_fstab = run_on_host(host, "findmnt --fstab -rn --target %s", path).rc == 0
        fields.append((f"Storage {name}", path))
        fields.append(("  Source", str(mount.get("source", ""))))
        fields.append(("  Mounted", "YES" if mounted else "no"))
        fields.append(("  fstab entry", "PRESENT" if in_fstab else "absent"))
        if mounted or in_fstab:
            failures.append(f"{name}: storage still attached")

    missing = sorted(names - resolved)
    if missing:
        failures.append("unresolved storage: " + ", ".join(missing))
    if not names:
        fields.append(("Referenced storage", "none configured"))
    fields.append(
        (
            "Shared-data result",
            (
                "delete requested; playbook enforces deletion before detachment"
                if delete_requested
                else "preserved; only storage detachment was requested"
            ),
        )
    )

    return _result(
        not failures,
        f"{component} policy and {len(resolved)} storage mount(s) checked",
        fields,
        "; ".join(failures),
    )


def check_cleanup_slurm(host) -> dict[str, Any]:
    """Verify the configured Slurm cleanup policy and storage detachment."""
    return _check_cleanup_storage(host, "slurm")


def check_cleanup_kubernetes(host) -> dict[str, Any]:
    """Verify the configured Kubernetes cleanup policy and storage detachment."""
    return _check_cleanup_storage(host, "kubernetes")


def check_cleanup_artifacts(host) -> dict[str, Any]:
    """Verify generated outputs were removed while source inputs remain."""
    input_path = resolve_target_input_project_path(host)
    output_path = resolve_target_output_project_path(host)
    shared_path = resolve_target_shared_path(host)
    fields: list[tuple[str, object]] = []
    failures: list[str] = []

    for path in (
        output_path,
        os.path.join(shared_path, "log", "cleanup"),
        "/var/lib/omnia/cleanup",
    ):
        removed = not host.file(path).exists
        fields.append((path, "removed" if removed else "STILL EXISTS"))
        if not removed:
            failures.append(f"generated path: {path}")

    for name in PRESERVED_INPUT_FILES:
        path = os.path.join(input_path, name)
        present = host.file(path).is_file
        fields.append((path, "preserved" if present else "MISSING"))
        if not present:
            failures.append(f"input: {path}")

    return _result(
        not failures,
        "Generated cleanup state and required project inputs checked",
        fields,
        "; ".join(failures),
    )


def check_cleanup_credentials(host) -> dict[str, Any]:
    """Verify credential artifacts follow the selected full-cleanup policy."""
    config = load_test_config()
    remove_credentials = config.get("cleanup_credentials", True)
    input_path = resolve_target_input_project_path(host)
    fields: list[tuple[str, object]] = [
        (
            "Expected policy",
            "remove" if remove_credentials else "preserve",
        )
    ]
    failures: list[str] = []

    for name in CREDENTIAL_FILES:
        path = os.path.join(input_path, name)
        exists = host.file(path).exists
        if remove_credentials:
            okay = not exists
            state = "removed" if okay else "STILL EXISTS"
        elif name.endswith(".lock"):
            okay = True
            state = "present" if exists else "not present (optional lock)"
        else:
            okay = exists
            state = "preserved" if okay else "MISSING"
        fields.append((path, state))
        if not okay:
            failures.append(path)

    return _result(
        not failures,
        "Orchestrator credential artifacts checked",
        fields,
        "Credential policy mismatch: " + ", ".join(failures) if failures else "",
    )
