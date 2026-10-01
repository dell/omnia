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

"""Precheck validation for mount_config storage_config.yml schema.

Verifies that mount entries in storage_config.yml satisfy the mandatory
field contracts enforced by the mount_config role.  These are read-only
checks against the input file on the OIM --- no orchestrator playbook is
executed.

Each check validates one mandatory-field or consistency rule:
  - mount_point is present and is an absolute path
  - source is present and non-empty
  - targeting (functional_group_prefix OR groups) is present
  - mount_params profile reference resolves to an existing profile
  - node_mount_point is present when node_key is set
"""

import os
import re
from typing import Any

from ..vars.pxeboot_vars import STORAGE_CONFIG
from ._prepare_helpers import prepare_result, read_yaml_mapping
from .project_func import resolve_target_input_project_path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_storage_config(host) -> dict[str, Any]:
    """Load storage_config.yml from the project input directory."""
    input_dir = resolve_target_input_project_path(host)
    path = os.path.join(input_dir, STORAGE_CONFIG)
    return read_yaml_mapping(host, path)


def _get_mounts(storage_config: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the raw mounts list (unfiltered)."""
    mounts = storage_config.get("mounts")
    if not isinstance(mounts, list):
        return []
    return [m for m in mounts if isinstance(m, dict)]


# ---------------------------------------------------------------------------
# Public check functions
# ---------------------------------------------------------------------------


def check_precheck_mount_missing_mount_point(host) -> dict[str, Any]:
    """TC-CI-NEG-001: Verify every mount entry has a valid mount_point."""
    summary = "Mount entry mount_point validation"
    try:
        storage_config = _load_storage_config(host)
        mounts = _get_mounts(storage_config)
        if not mounts:
            return prepare_result(
                True,
                summary,
                [("Mount entries", 0), ("Validation", "skipped (no mounts)")],
            )

        fields: list[tuple[str, object]] = [("Mount entries", len(mounts))]
        violations = []
        for idx, mount in enumerate(mounts):
            name = mount.get("name", f"entry[{idx}]")
            mp = mount.get("mount_point")
            if not mp or not isinstance(mp, str):
                violations.append(name)
                fields.append((
                    f"  {name}",
                    "FAIL: mount_point is missing or empty",
                ))
            elif not mp.startswith("/"):
                violations.append(name)
                fields.append((
                    f"  {name}",
                    f"FAIL: mount_point '{mp}' is not an absolute path",
                ))
            else:
                fields.append((f"  {name}", f"OK: {mp}"))

        return prepare_result(
            not violations,
            summary,
            fields,
            (
                f"Mount entries missing valid mount_point: "
                f"{', '.join(violations)}"
            )
            if violations
            else "",
        )
    except (OSError, TypeError, ValueError) as exc:
        return prepare_result(False, summary, [], str(exc))


def check_precheck_mount_missing_source(host) -> dict[str, Any]:
    """TC-CI-NEG-004: Verify every mount entry has a non-empty source."""
    summary = "Mount entry source validation"
    try:
        storage_config = _load_storage_config(host)
        mounts = _get_mounts(storage_config)
        if not mounts:
            return prepare_result(
                True,
                summary,
                [("Mount entries", 0), ("Validation", "skipped (no mounts)")],
            )

        fields: list[tuple[str, object]] = [("Mount entries", len(mounts))]
        violations = []
        for idx, mount in enumerate(mounts):
            name = mount.get("name", f"entry[{idx}]")
            source = mount.get("source")
            if not source or not isinstance(source, str):
                violations.append(name)
                fields.append((
                    f"  {name}",
                    "FAIL: source is missing or empty",
                ))
            else:
                fields.append((f"  {name}", f"OK: {source}"))

        return prepare_result(
            not violations,
            summary,
            fields,
            (
                f"Mount entries missing source: "
                f"{', '.join(violations)}"
            )
            if violations
            else "",
        )
    except (OSError, TypeError, ValueError) as exc:
        return prepare_result(False, summary, [], str(exc))


def check_precheck_mount_missing_targeting(host) -> dict[str, Any]:
    """TC-CI-NEG-002: Verify every mount entry has targeting configured.

    Each mount must have either ``functional_group_prefix`` (list) or
    ``groups`` (list).  Both being absent or both being present is a
    configuration error.
    """
    summary = "Mount entry targeting validation"
    try:
        storage_config = _load_storage_config(host)
        mounts = _get_mounts(storage_config)
        if not mounts:
            return prepare_result(
                True,
                summary,
                [("Mount entries", 0), ("Validation", "skipped (no mounts)")],
            )

        fields: list[tuple[str, object]] = [("Mount entries", len(mounts))]
        violations = []
        for idx, mount in enumerate(mounts):
            name = mount.get("name", f"entry[{idx}]")
            fgp = mount.get("functional_group_prefix")
            grp = mount.get("groups")
            has_fgp = isinstance(fgp, list) and bool(fgp)
            has_grp = isinstance(grp, list) and bool(grp)

            if has_fgp and has_grp:
                violations.append(name)
                fields.append((
                    f"  {name}",
                    "FAIL: both functional_group_prefix and groups set "
                    "(mutually exclusive)",
                ))
            elif not has_fgp and not has_grp:
                violations.append(name)
                fields.append((
                    f"  {name}",
                    "FAIL: neither functional_group_prefix nor groups set",
                ))
            elif has_fgp:
                fields.append((
                    f"  {name}",
                    f"OK: functional_group_prefix={fgp}",
                ))
            else:
                fields.append((f"  {name}", f"OK: groups={grp}"))

        return prepare_result(
            not violations,
            summary,
            fields,
            (
                f"Mount entries with targeting issues: "
                f"{', '.join(violations)}"
            )
            if violations
            else "",
        )
    except (OSError, TypeError, ValueError) as exc:
        return prepare_result(False, summary, [], str(exc))


def check_precheck_mount_invalid_mount_params(host) -> dict[str, Any]:
    """TC-CI-NEG-003: Verify mount_params references resolve to existing profiles."""
    summary = "Mount params profile resolution"
    try:
        storage_config = _load_storage_config(host)
        mounts = _get_mounts(storage_config)
        mount_params = storage_config.get("mount_params", {})
        if not isinstance(mount_params, dict):
            mount_params = {}

        if not mounts:
            return prepare_result(
                True,
                summary,
                [("Mount entries", 0), ("Validation", "skipped (no mounts)")],
            )

        # Only check entries that reference a profile
        profiled = [
            m for m in mounts if m.get("mount_params")
        ]
        if not profiled:
            return prepare_result(
                True,
                summary,
                [
                    ("Mount entries", len(mounts)),
                    ("With mount_params", 0),
                    ("Validation", "skipped (no profiles referenced)"),
                ],
            )

        fields: list[tuple[str, object]] = [
            ("Mount entries", len(mounts)),
            ("With mount_params", len(profiled)),
            ("Available profiles", ", ".join(sorted(mount_params.keys()))
             if mount_params else "(none)"),
        ]
        violations = []
        for idx, mount in enumerate(mounts):
            name = mount.get("name", f"entry[{idx}]")
            profile_name = mount.get("mount_params")
            if not profile_name:
                continue
            if profile_name in mount_params:
                fields.append((
                    f"  {name}",
                    f"OK: mount_params='{profile_name}' resolved",
                ))
            else:
                violations.append(name)
                fields.append((
                    f"  {name}",
                    f"FAIL: mount_params='{profile_name}' not found in "
                    f"mount_params section",
                ))

        return prepare_result(
            not violations,
            summary,
            fields,
            (
                f"Unresolvable mount_params profiles: "
                f"{', '.join(violations)}"
            )
            if violations
            else "",
        )
    except (OSError, TypeError, ValueError) as exc:
        return prepare_result(False, summary, [], str(exc))


def check_precheck_mount_node_key_without_mount_point(host) -> dict[str, Any]:
    """TC-CI-NEG-005: Verify node_mount_point is set when node_key is specified."""
    summary = "Mount node_key / node_mount_point consistency"
    try:
        storage_config = _load_storage_config(host)
        mounts = _get_mounts(storage_config)
        if not mounts:
            return prepare_result(
                True,
                summary,
                [("Mount entries", 0), ("Validation", "skipped (no mounts)")],
            )

        # Only check entries with node_key
        keyed = [m for m in mounts if m.get("node_key")]
        if not keyed:
            return prepare_result(
                True,
                summary,
                [
                    ("Mount entries", len(mounts)),
                    ("With node_key", 0),
                    ("Validation", "skipped (no node_key entries)"),
                ],
            )

        fields: list[tuple[str, object]] = [
            ("Mount entries", len(mounts)),
            ("With node_key", len(keyed)),
        ]
        violations = []
        for idx, mount in enumerate(mounts):
            name = mount.get("name", f"entry[{idx}]")
            node_key = mount.get("node_key")
            if not node_key:
                continue
            nmp = mount.get("node_mount_point")
            if not isinstance(nmp, list) or not nmp:
                violations.append(name)
                fields.append((
                    f"  {name}",
                    f"FAIL: node_key='{node_key}' set but node_mount_point "
                    f"is missing or empty",
                ))
            else:
                # Validate each entry is an absolute path
                bad_paths = [p for p in nmp if not str(p).startswith("/")]
                if bad_paths:
                    violations.append(name)
                    fields.append((
                        f"  {name}",
                        f"FAIL: node_mount_point contains non-absolute paths: "
                        f"{bad_paths}",
                    ))
                else:
                    fields.append((
                        f"  {name}",
                        f"OK: node_key='{node_key}', "
                        f"node_mount_point={nmp}",
                    ))

        return prepare_result(
            not violations,
            summary,
            fields,
            (
                f"node_key entries missing valid node_mount_point: "
                f"{', '.join(violations)}"
            )
            if violations
            else "",
        )
    except (OSError, TypeError, ValueError) as exc:
        return prepare_result(False, summary, [], str(exc))
