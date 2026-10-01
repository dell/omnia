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

The validation logic is also exercised against controlled malformed fixtures
(see ``validate_*`` helpers) so that negative tests can prove the validators
reject bad input.
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
# Pure validation helpers (testable without a host)
# ---------------------------------------------------------------------------


def validate_mount_points(mounts: list[dict[str, Any]]) -> list[str]:
    """Return violation descriptions for mounts missing a valid mount_point."""
    violations = []
    for idx, mount in enumerate(mounts):
        name = mount.get("name", f"entry[{idx}]")
        mp = mount.get("mount_point")
        if not mp or not isinstance(mp, str):
            violations.append(f"{name}: mount_point is missing or empty")
        elif not mp.startswith("/"):
            violations.append(f"{name}: mount_point '{mp}' is not absolute")
    return violations


def validate_sources(mounts: list[dict[str, Any]]) -> list[str]:
    """Return violation descriptions for mounts missing a non-empty source."""
    violations = []
    for idx, mount in enumerate(mounts):
        name = mount.get("name", f"entry[{idx}]")
        source = mount.get("source")
        if not source or not isinstance(source, str):
            violations.append(f"{name}: source is missing or empty")
    return violations


def validate_targeting(mounts: list[dict[str, Any]]) -> list[str]:
    """Return violation descriptions for mounts without valid targeting."""
    violations = []
    for idx, mount in enumerate(mounts):
        name = mount.get("name", f"entry[{idx}]")
        fgp = mount.get("functional_group_prefix")
        grp = mount.get("groups")
        has_fgp = isinstance(fgp, list) and bool(fgp)
        has_grp = isinstance(grp, list) and bool(grp)
        if has_fgp and has_grp:
            violations.append(
                f"{name}: both functional_group_prefix and groups set"
            )
        elif not has_fgp and not has_grp:
            violations.append(
                f"{name}: neither functional_group_prefix nor groups set"
            )
    return violations


def validate_mount_params(
    mounts: list[dict[str, Any]],
    mount_params: dict[str, Any],
) -> list[str]:
    """Return violation descriptions for unresolvable mount_params profiles."""
    violations = []
    for idx, mount in enumerate(mounts):
        name = mount.get("name", f"entry[{idx}]")
        profile_name = mount.get("mount_params")
        if not profile_name:
            continue
        if profile_name not in mount_params:
            violations.append(
                f"{name}: mount_params='{profile_name}' not found"
            )
    return violations


def validate_node_key_consistency(
    mounts: list[dict[str, Any]],
) -> list[str]:
    """Return violation descriptions for node_key without node_mount_point."""
    violations = []
    for idx, mount in enumerate(mounts):
        name = mount.get("name", f"entry[{idx}]")
        node_key = mount.get("node_key")
        if not node_key:
            continue
        nmp = mount.get("node_mount_point")
        if not isinstance(nmp, list) or not nmp:
            violations.append(
                f"{name}: node_key='{node_key}' set but "
                f"node_mount_point is missing or empty"
            )
        else:
            bad_paths = [p for p in nmp if not str(p).startswith("/")]
            if bad_paths:
                violations.append(
                    f"{name}: node_mount_point contains "
                    f"non-absolute paths: {bad_paths}"
                )
    return violations


# ---------------------------------------------------------------------------
# Public check functions (read live config, delegate to validators)
# ---------------------------------------------------------------------------


def check_precheck_mount_missing_mount_point(host) -> dict[str, Any]:
    """TC-CI-NEG-001: Verify every mount entry has a valid mount_point.

    First validates the live config on the OIM, then exercises the
    validator against a controlled malformed fixture to prove the
    rejection path works.
    """
    summary = "Mount entry mount_point validation"
    try:
        storage_config = _load_storage_config(host)
        mounts = _get_mounts(storage_config)

        # --- Phase 1: validate live config ---
        fields: list[tuple[str, object]] = [("Mount entries", len(mounts))]
        live_violations = validate_mount_points(mounts) if mounts else []
        for v in live_violations:
            fields.append(("  Live", f"FAIL: {v}"))
        if not live_violations and mounts:
            fields.append(("  Live config", "OK"))

        # --- Phase 2: controlled malformed fixture ---
        bad_mounts = [
            {"name": "fixture_no_mp", "source": "10.0.0.1:/x"},
            {"name": "fixture_relative_mp", "source": "10.0.0.1:/x",
             "mount_point": "relative/path"},
        ]
        fixture_violations = validate_mount_points(bad_mounts)
        fixture_ok = len(fixture_violations) == 2
        fields.append((
            "  Fixture rejection",
            f"{'OK' if fixture_ok else 'FAIL'}: "
            f"{len(fixture_violations)}/2 violations detected",
        ))

        all_ok = not live_violations and fixture_ok
        error = ""
        if live_violations:
            error = "Live: " + "; ".join(live_violations)
        if not fixture_ok:
            error += ("; " if error else "") + "Fixture rejection failed"

        return prepare_result(all_ok, summary, fields, error)
    except (OSError, TypeError, ValueError) as exc:
        return prepare_result(False, summary, [], str(exc))


def check_precheck_mount_missing_source(host) -> dict[str, Any]:
    """TC-CI-NEG-004: Verify every mount entry has a non-empty source.

    Validates the live config, then exercises the validator against a
    controlled malformed fixture.
    """
    summary = "Mount entry source validation"
    try:
        storage_config = _load_storage_config(host)
        mounts = _get_mounts(storage_config)

        fields: list[tuple[str, object]] = [("Mount entries", len(mounts))]
        live_violations = validate_sources(mounts) if mounts else []
        for v in live_violations:
            fields.append(("  Live", f"FAIL: {v}"))
        if not live_violations and mounts:
            fields.append(("  Live config", "OK"))

        bad_mounts = [
            {"name": "fixture_no_src", "mount_point": "/mnt/x"},
            {"name": "fixture_empty_src", "mount_point": "/mnt/y", "source": ""},
        ]
        fixture_violations = validate_sources(bad_mounts)
        fixture_ok = len(fixture_violations) == 2
        fields.append((
            "  Fixture rejection",
            f"{'OK' if fixture_ok else 'FAIL'}: "
            f"{len(fixture_violations)}/2 violations detected",
        ))

        all_ok = not live_violations and fixture_ok
        error = ""
        if live_violations:
            error = "Live: " + "; ".join(live_violations)
        if not fixture_ok:
            error += ("; " if error else "") + "Fixture rejection failed"

        return prepare_result(all_ok, summary, fields, error)
    except (OSError, TypeError, ValueError) as exc:
        return prepare_result(False, summary, [], str(exc))


def check_precheck_mount_missing_targeting(host) -> dict[str, Any]:
    """TC-CI-NEG-002: Verify every mount entry has targeting configured.

    Each mount must have either ``functional_group_prefix`` (list) or
    ``groups`` (list).  Both being absent or both being present is a
    configuration error.

    Validates the live config, then exercises the validator against
    controlled malformed fixtures.
    """
    summary = "Mount entry targeting validation"
    try:
        storage_config = _load_storage_config(host)
        mounts = _get_mounts(storage_config)

        fields: list[tuple[str, object]] = [("Mount entries", len(mounts))]
        live_violations = validate_targeting(mounts) if mounts else []
        for v in live_violations:
            fields.append(("  Live", f"FAIL: {v}"))
        if not live_violations and mounts:
            fields.append(("  Live config", "OK"))

        bad_mounts = [
            {"name": "fixture_no_targeting", "mount_point": "/mnt/x",
             "source": "10.0.0.1:/x"},
            {"name": "fixture_both", "mount_point": "/mnt/y",
             "source": "10.0.0.1:/y",
             "functional_group_prefix": ["slurm_"], "groups": ["grp0"]},
        ]
        fixture_violations = validate_targeting(bad_mounts)
        fixture_ok = len(fixture_violations) == 2
        fields.append((
            "  Fixture rejection",
            f"{'OK' if fixture_ok else 'FAIL'}: "
            f"{len(fixture_violations)}/2 violations detected",
        ))

        all_ok = not live_violations and fixture_ok
        error = ""
        if live_violations:
            error = "Live: " + "; ".join(live_violations)
        if not fixture_ok:
            error += ("; " if error else "") + "Fixture rejection failed"

        return prepare_result(all_ok, summary, fields, error)
    except (OSError, TypeError, ValueError) as exc:
        return prepare_result(False, summary, [], str(exc))


def check_precheck_mount_invalid_mount_params(host) -> dict[str, Any]:
    """TC-CI-NEG-003: Verify mount_params references resolve to existing profiles.

    Validates the live config, then exercises the validator against a
    controlled malformed fixture with a nonexistent profile reference.
    """
    summary = "Mount params profile resolution"
    try:
        storage_config = _load_storage_config(host)
        mounts = _get_mounts(storage_config)
        mount_params = storage_config.get("mount_params", {})
        if not isinstance(mount_params, dict):
            mount_params = {}

        fields: list[tuple[str, object]] = [
            ("Mount entries", len(mounts)),
            ("Available profiles", ", ".join(sorted(mount_params.keys()))
             if mount_params else "(none)"),
        ]
        live_violations = (
            validate_mount_params(mounts, mount_params) if mounts else []
        )
        for v in live_violations:
            fields.append(("  Live", f"FAIL: {v}"))
        if not live_violations and mounts:
            fields.append(("  Live config", "OK"))

        bad_mounts = [
            {"name": "fixture_bad_profile", "mount_point": "/mnt/x",
             "source": "10.0.0.1:/x", "mount_params": "nonexistent_profile"},
        ]
        fixture_violations = validate_mount_params(bad_mounts, mount_params)
        fixture_ok = len(fixture_violations) == 1
        fields.append((
            "  Fixture rejection",
            f"{'OK' if fixture_ok else 'FAIL'}: "
            f"{len(fixture_violations)}/1 violations detected",
        ))

        all_ok = not live_violations and fixture_ok
        error = ""
        if live_violations:
            error = "Live: " + "; ".join(live_violations)
        if not fixture_ok:
            error += ("; " if error else "") + "Fixture rejection failed"

        return prepare_result(all_ok, summary, fields, error)
    except (OSError, TypeError, ValueError) as exc:
        return prepare_result(False, summary, [], str(exc))


def check_precheck_mount_node_key_without_mount_point(host) -> dict[str, Any]:
    """TC-CI-NEG-005: Verify node_mount_point is set when node_key is specified.

    Validates the live config, then exercises the validator against a
    controlled malformed fixture.
    """
    summary = "Mount node_key / node_mount_point consistency"
    try:
        storage_config = _load_storage_config(host)
        mounts = _get_mounts(storage_config)

        fields: list[tuple[str, object]] = [("Mount entries", len(mounts))]
        live_violations = (
            validate_node_key_consistency(mounts) if mounts else []
        )
        for v in live_violations:
            fields.append(("  Live", f"FAIL: {v}"))
        if not live_violations and mounts:
            fields.append(("  Live config", "OK"))

        bad_mounts = [
            {"name": "fixture_key_no_nmp", "mount_point": "/mnt/x",
             "source": "10.0.0.1:/x", "node_key": "ds.meta-data.local-hostname"},
            {"name": "fixture_key_relative_nmp", "mount_point": "/mnt/y",
             "source": "10.0.0.1:/y", "node_key": "ds.meta-data.local-hostname",
             "node_mount_point": ["relative/path"]},
        ]
        fixture_violations = validate_node_key_consistency(bad_mounts)
        fixture_ok = len(fixture_violations) == 2
        fields.append((
            "  Fixture rejection",
            f"{'OK' if fixture_ok else 'FAIL'}: "
            f"{len(fixture_violations)}/2 violations detected",
        ))

        all_ok = not live_violations and fixture_ok
        error = ""
        if live_violations:
            error = "Live: " + "; ".join(live_violations)
        if not fixture_ok:
            error += ("; " if error else "") + "Fixture rejection failed"

        return prepare_result(all_ok, summary, fields, error)
    except (OSError, TypeError, ValueError) as exc:
        return prepare_result(False, summary, [], str(exc))
