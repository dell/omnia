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
"""L2 validation for the Orchestrator storage configuration."""

from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from logging import Logger
from typing import Any

from ..messages import orchestrator_messages as msg
from .network_spec_validator import record_error
from .pxe_mapping_validator import (
    CANONICAL_HEADERS,
    read_mapping,
    resolve_mapping_path,
)

BUILTIN_FUNCTIONAL_GROUPS = {
    "service_kube_control_plane_first_x86_64",
    "service_kube_control_plane_x86_64",
    "service_kube_node_x86_64",
    "login_node_x86_64",
    "login_node_aarch64",
    "login_compiler_node_x86_64",
    "login_compiler_node_aarch64",
    "slurm_control_node_x86_64",
    "slurm_node_x86_64",
    "slurm_node_aarch64",
    "os_x86_64",
    "os_aarch64",
}
SIZE_MULTIPLIERS = {
    "B": 1,
    "K": 1024,
    "M": 1024**2,
    "G": 1024**3,
    "T": 1024**4,
}


def _catalog_functional_groups(
    orchestrator_data: dict[str, Any],
) -> set[str]:
    """Load active catalog functional groups when a catalog is available."""
    configured_path = orchestrator_data.get("catalog_file_path", "")
    environment_path = os.getenv("CATALOG_FILE_PATH", "")
    omnia_data_path = os.getenv("OMNIA_DATA_PATH", "") or "/opt/omnia"
    path = os.path.realpath(
        configured_path
        or environment_path
        or os.path.join(omnia_data_path, "catalog", "catalog_rhel.json")
    )
    if not os.path.isfile(path):
        return set()
    try:
        with open(path, "r", encoding="utf-8") as catalog_file:
            data = json.load(catalog_file)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return set()

    catalog = data.get("catalog", {}) if isinstance(data, dict) else {}
    layers = catalog.get("functionallayer", []) if isinstance(catalog, dict) else []
    return {
        layer["name"].strip()
        for layer in layers
        if isinstance(layer, dict)
        and isinstance(layer.get("name"), str)
        and layer["name"].strip()
    }


def _mapping_targets(
    orchestrator_data: dict[str, Any], input_project_dir: str
) -> tuple[set[str], set[str]] | None:
    """Return mapping functional groups and logical groups when CSV is valid."""
    path = resolve_mapping_path(orchestrator_data, input_project_dir)
    if not os.path.isfile(path):
        return None
    try:
        raw_header, header, rows = read_mapping(path)
    except (csv.Error, OSError, UnicodeError):
        return None
    if raw_header != list(CANONICAL_HEADERS):
        return None
    if any(len(row) != len(header) for _, row in rows):
        return None

    mapped_rows = [dict(zip(header, row)) for _, row in rows]
    return (
        {
            row.get("FUNCTIONAL_GROUP_NAME", "")
            for row in mapped_rows
            if row.get("FUNCTIONAL_GROUP_NAME", "")
        },
        {row.get("GROUP_NAME", "") for row in mapped_rows if row.get("GROUP_NAME", "")},
    )


def _entry_name(section: str, index: int, entry: dict[str, Any]) -> str:
    """Return a stable storage-entry label for validation messages."""
    return str(entry.get("name") or entry.get("filename") or f"{section}[{index}]")


def _prefix_matches(prefix: str, functional_group: str) -> bool:
    """Apply the prefix semantics used by the current mount runtime."""
    return functional_group.startswith(prefix)


def _expand_prefixes(
    prefixes: list[str], known_functional_groups: set[str]
) -> set[str]:
    """Expand target prefixes to known functional-group names."""
    return {
        functional_group
        for prefix in prefixes
        for functional_group in known_functional_groups
        if _prefix_matches(prefix, functional_group)
    }


def _effective_storage_data(
    storage_data: dict[str, Any], omnia_data: dict[str, Any]
) -> dict[str, Any]:
    """Mirror runtime selection of the stock VAST mount for semantic checks.

    The complete storage document is still schema-validated.  Only the L2
    target and collision checks omit the managed ``vast_storage`` entry when
    the first Slurm cluster does not select it, matching ``mount_config``.
    """
    slurm_clusters = omnia_data.get("slurm_cluster", [])
    active_cluster = (
        slurm_clusters[0]
        if isinstance(slurm_clusters, list)
        and slurm_clusters
        and isinstance(slurm_clusters[0], dict)
        else {}
    )
    configured_vast_name = active_cluster.get("vast_storage_name", "")
    if not isinstance(configured_vast_name, str):
        configured_vast_name = ""
    configured_vast_name = configured_vast_name.strip()

    effective_data = dict(storage_data)
    mounts = storage_data.get("mounts", [])
    if isinstance(mounts, list):
        effective_data["mounts"] = [
            entry
            for entry in mounts
            if not (
                isinstance(entry, dict)
                and entry.get("name") == "vast_storage"
                and configured_vast_name != "vast_storage"
            )
        ]
    return effective_data


def _validate_targets(
    storage_data: dict[str, Any],
    known_functional_groups: set[str],
    mapped_groups: set[str] | None,
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Validate functional-group prefixes and PXE logical-group names."""
    for section in ("mounts", "powervault_config", "swap"):
        entries = storage_data.get(section, [])
        if not isinstance(entries, list):
            continue
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                continue
            name = _entry_name(section, index, entry)
            for prefix in entry.get("functional_group_prefix", []):
                if not _expand_prefixes([prefix], known_functional_groups):
                    record_error(
                        errors,
                        logger,
                        msg.storage_unknown_prefix_msg(section, name, prefix),
                    )
            if mapped_groups is None:
                continue
            for group in entry.get("groups", []):
                if group not in mapped_groups:
                    record_error(
                        errors,
                        logger,
                        msg.storage_unknown_group_msg(
                            section, name, group, sorted(mapped_groups)
                        ),
                    )


def _validate_duplicate_mount_points(
    storage_data: dict[str, Any],
    known_functional_groups: set[str],
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Reject duplicate mount destinations for the same target."""
    target_mounts: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for section in ("mounts", "powervault_config"):
        entries = storage_data.get(section, [])
        if not isinstance(entries, list):
            continue
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                continue
            name = _entry_name(section, index, entry)
            destinations = [entry.get("mount_point", "")]
            destinations.extend(entry.get("node_mount_point", []))
            destinations = [str(path) for path in destinations if path]
            targets = _expand_prefixes(
                entry.get("functional_group_prefix", []),
                known_functional_groups,
            )
            targets.update(entry.get("groups", []))
            for target in targets:
                for destination in destinations:
                    target_mounts[target].append((destination, name, section))

    for target, entries in sorted(target_mounts.items()):
        by_destination: dict[str, list[str]] = defaultdict(list)
        for destination, name, section in entries:
            by_destination[destination].append(f"{name}({section})")
        for destination, names in sorted(by_destination.items()):
            if len(names) > 1:
                record_error(
                    errors,
                    logger,
                    msg.storage_duplicate_mount_point_msg(target, destination, names),
                )


def _size_to_bytes(value: str | int) -> int:
    """Convert a schema-validated swap size to bytes."""
    if isinstance(value, int):
        return value
    if value == "auto":
        return 0
    suffix = value[-1]
    if suffix in SIZE_MULTIPLIERS:
        return int(value[:-1]) * SIZE_MULTIPLIERS[suffix]
    return int(value)


def _validate_swap(
    storage_data: dict[str, Any],
    errors: list[str],
    logger: Logger | None,
) -> None:
    """Validate swap target overlap and configured size limits."""
    seen_prefixes: dict[str, str] = {}
    entries = storage_data.get("swap", [])
    if not isinstance(entries, list):
        return
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        name = _entry_name("swap", index, entry)
        for prefix in entry.get("functional_group_prefix", []):
            previous_name = seen_prefixes.get(prefix)
            if previous_name is not None:
                record_error(
                    errors,
                    logger,
                    msg.storage_swap_overlap_msg(prefix, name, previous_name),
                )
            else:
                seen_prefixes[prefix] = name

        size = entry.get("size")
        maxsize = entry.get("maxsize")
        if maxsize is None or size in (None, "auto"):
            continue
        if _size_to_bytes(maxsize) < _size_to_bytes(size):
            record_error(
                errors,
                logger,
                msg.storage_swap_size_msg(name, str(size), str(maxsize)),
            )


def validate(
    storage_data: Any,
    orchestrator_data: dict[str, Any],
    omnia_data: dict[str, Any],
    input_project_dir: str,
    logger: Logger | None = None,
) -> list[str]:
    """Run semantic validation for the storage configuration."""
    errors: list[str] = []
    if not isinstance(storage_data, dict):
        return errors

    mapping_targets = _mapping_targets(orchestrator_data, input_project_dir)
    mapped_functional_groups: set[str] = set()
    mapped_groups: set[str] | None = None
    if mapping_targets is not None:
        mapped_functional_groups, mapped_groups = mapping_targets

    known_functional_groups = set(BUILTIN_FUNCTIONAL_GROUPS)
    known_functional_groups.update(mapped_functional_groups)
    known_functional_groups.update(_catalog_functional_groups(orchestrator_data))

    effective_storage_data = _effective_storage_data(
        storage_data,
        omnia_data if isinstance(omnia_data, dict) else {},
    )

    _validate_targets(
        effective_storage_data,
        known_functional_groups,
        mapped_groups,
        errors,
        logger,
    )
    _validate_duplicate_mount_points(
        effective_storage_data, known_functional_groups, errors, logger
    )
    _validate_swap(effective_storage_data, errors, logger)
    return errors
