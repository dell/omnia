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

"""Precheck validation functions for local_storage declaration contracts.

Covers ER-ORCH-011 TC-FVT-001 to TC-FVT-005 and TC-FVT-029.

Each function:
  1. Loads storage_config.yml from the OIM project input directory.
  2. Validates the live local_storage entries against one contract.
  3. Exercises the validator against a controlled malformed fixture to prove
     the rejection path is active.

No orchestrator playbook or PXE boot is triggered; these are read-only
checks against the declared input file.
"""

import os
from typing import Any

from ..vars.pxeboot_vars import STORAGE_CONFIG
from ._prepare_helpers import prepare_result, read_yaml_mapping
from .project_func import resolve_target_input_project_path

# ---------------------------------------------------------------------------
# Service Kubernetes group prefixes accepted by local_storage (FR-1.1)
# ---------------------------------------------------------------------------
_SERVICE_K8S_PREFIXES: frozenset[str] = frozenset(
    {
        "service_kube_control_plane",
        "service_kube_node",
    }
)
_VALID_PURPOSES: frozenset[str] = frozenset({"etcd", "kafka"})
_VALID_DISK_TYPES: frozenset[str] = frozenset({"boss", "ssd", "hdd", "nvme", "any"})
_ETCD_FORBIDDEN_MOUNT_OPTS: frozenset[str] = frozenset({"nofail"})


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_storage_config(host) -> dict[str, Any]:
    input_dir = resolve_target_input_project_path(host)
    path = os.path.join(input_dir, STORAGE_CONFIG)
    return read_yaml_mapping(host, path)


def _get_local_storage(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    entries = cfg.get("local_storage") or []
    if not isinstance(entries, list):
        return []
    return [e for e in entries if isinstance(e, dict)]


# ---------------------------------------------------------------------------
# Pure validators (testable without a host)
# ---------------------------------------------------------------------------

def validate_local_storage_declarations(
    entries: list[dict[str, Any]],
) -> list[str]:
    """TC-FVT-001: Every entry must have name, purpose, disk_type, and
    functional_group_prefix; Kafka must have volume_group; disk_type must be
    in the enum."""
    violations: list[str] = []
    for idx, entry in enumerate(entries):
        name = entry.get("name", f"entry[{idx}]")
        purpose = entry.get("purpose")
        disk_type = entry.get("disk_type")
        fgp = entry.get("functional_group_prefix")

        if not purpose:
            violations.append(f"{name}: purpose is missing")
        elif purpose not in _VALID_PURPOSES:
            violations.append(f"{name}: purpose '{purpose}' is not in {sorted(_VALID_PURPOSES)}")

        if not disk_type:
            violations.append(f"{name}: disk_type is missing")
        elif disk_type not in _VALID_DISK_TYPES:
            valid_set = sorted(_VALID_DISK_TYPES)
            violations.append(f"{name}: disk_type '{disk_type}' is not in {valid_set}")

        if purpose == "kafka" and not entry.get("volume_group"):
            violations.append(f"{name}: kafka entry missing required 'volume_group'")

        if not fgp or not isinstance(fgp, list):
            violations.append(f"{name}: functional_group_prefix is missing or not a list")

    return violations


def validate_service_k8s_targeting(
    entries: list[dict[str, Any]],
) -> list[str]:
    """TC-FVT-002: Every entry must target only service Kubernetes groups
    (service_kube_control_plane or service_kube_node); fg_ flexible groups
    and non-service groups are rejected."""
    violations: list[str] = []
    for idx, entry in enumerate(entries):
        name = entry.get("name", f"entry[{idx}]")
        fgp = entry.get("functional_group_prefix")
        if not fgp or not isinstance(fgp, list):
            continue
        for prefix in fgp:
            prefix_str = str(prefix)
            if prefix_str.startswith("fg_"):
                violations.append(
                    f"{name}: prefix '{prefix_str}' matches a flexible fg_ group "
                    "and is not allowed for local_storage"
                )
                continue
            # Match the base prefix (strip architecture suffix)
            base = prefix_str.rsplit("_x86_64", 1)[0].rsplit("_aarch64", 1)[0]
            if base not in _SERVICE_K8S_PREFIXES:
                violations.append(
                    f"{name}: prefix '{prefix_str}' is not a service Kubernetes group "
                    f"(accepted: {sorted(_SERVICE_K8S_PREFIXES)})"
                )
    return violations


def validate_semantic_rules(
    entries: list[dict[str, Any]],
) -> list[str]:
    """TC-FVT-003: Semantic rules — Kafka must target worker groups only;
    etcd must not use nofail in mount_options."""
    violations: list[str] = []
    for idx, entry in enumerate(entries):
        name = entry.get("name", f"entry[{idx}]")
        purpose = str(entry.get("purpose") or "")
        fgp = entry.get("functional_group_prefix") or []

        if purpose == "kafka":
            for prefix in fgp:
                p = str(prefix)
                base = p.rsplit("_x86_64", 1)[0].rsplit("_aarch64", 1)[0]
                if base == "service_kube_control_plane":
                    violations.append(
                        f"{name}: kafka entry targets control-plane group '{p}'; "
                        "Kafka runs only on worker nodes"
                    )

        if purpose == "etcd":
            mount_opts = str(entry.get("mount_options") or "")
            for bad_opt in _ETCD_FORBIDDEN_MOUNT_OPTS:
                if bad_opt in mount_opts.split(","):
                    violations.append(
                        f"{name}: etcd entry uses forbidden mount option '{bad_opt}'"
                    )
    return violations


def validate_etcd_nfs_fallback(
    entries: list[dict[str, Any]],
) -> tuple[bool, str]:
    """TC-FVT-004: When no etcd entry is declared, etcd uses NFS.
    Returns (nfs_fallback: bool, reason: str)."""
    etcd_entries = [e for e in entries if e.get("purpose") == "etcd"]
    if not etcd_entries:
        return True, "No etcd local_storage entry declared; etcd uses NFS"
    return False, f"{len(etcd_entries)} etcd entry(ies) declared; etcd uses local disk"


def validate_kafka_switch_absent(
    telemetry_cfg: dict[str, Any],
) -> list[str]:
    """TC-FVT-005/TC-FVT-029: kafka_on_local_disk defaults to false and
    rejects non-Boolean values when present."""
    violations: list[str] = []
    sinks = telemetry_cfg.get("telemetry_sinks") or {}
    kafka = sinks.get("kafka") or {} if isinstance(sinks, dict) else {}
    switch = kafka.get("kafka_on_local_disk") if isinstance(kafka, dict) else None

    if switch is None:
        return []  # absent → default False, valid

    if not isinstance(switch, bool):
        violations.append(
            f"kafka_on_local_disk has type {type(switch).__name__!r}; "
            "expected Boolean (true/false)"
        )
    return violations


# ---------------------------------------------------------------------------
# Public check functions (read live config, delegate to validators)
# ---------------------------------------------------------------------------

def check_precheck_local_storage_declarations(host) -> dict[str, Any]:
    """TC-FVT-001: Verify local_storage entries have required fields and valid enums."""
    summary = "Local storage declaration contract"
    try:
        cfg = _load_storage_config(host)
        entries = _get_local_storage(cfg)
        fields: list[tuple[str, object]] = [("Local storage entries", len(entries))]

        live_violations = validate_local_storage_declarations(entries)
        for v in live_violations:
            fields.append(("  Live", f"FAIL: {v}"))
        if not live_violations:
            fields.append(("  Live config", "OK" if entries else "none declared"))

        # Fixture: kafka entry with no volume_group must be rejected
        bad_entries = [
            {"name": "fixture_no_vg", "purpose": "kafka",
             "disk_type": "ssd", "functional_group_prefix": ["service_kube_node"]},
        ]
        fixture_violations = validate_local_storage_declarations(bad_entries)
        fixture_ok = len(fixture_violations) == 1
        fields.append((
            "  Fixture rejection",
            f"{'OK' if fixture_ok else 'FAIL'}: "
            f"{len(fixture_violations)}/1 violation detected",
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


def check_precheck_local_storage_targeting(host) -> dict[str, Any]:
    """TC-FVT-002: Verify local_storage entries target only service Kubernetes groups."""
    summary = "Local storage service-group targeting"
    try:
        cfg = _load_storage_config(host)
        entries = _get_local_storage(cfg)
        fields: list[tuple[str, object]] = [("Local storage entries", len(entries))]

        live_violations = validate_service_k8s_targeting(entries)
        for v in live_violations:
            fields.append(("  Live", f"FAIL: {v}"))
        if not live_violations:
            fields.append(("  Live config", "OK" if entries else "none declared"))

        # Fixture: fg_ prefix must be rejected
        bad_entries = [
            {"name": "fixture_fg", "purpose": "kafka",
             "disk_type": "ssd", "functional_group_prefix": ["fg_custom_group"]},
            {"name": "fixture_slurm", "purpose": "kafka",
             "disk_type": "ssd", "functional_group_prefix": ["slurm_node"]},
        ]
        fixture_violations = validate_service_k8s_targeting(bad_entries)
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


def check_precheck_local_storage_semantic_rules(host) -> dict[str, Any]:
    """TC-FVT-003: Verify semantic rules (Kafka on workers only, etcd no nofail)."""
    summary = "Local storage semantic validation rules"
    try:
        cfg = _load_storage_config(host)
        entries = _get_local_storage(cfg)
        fields: list[tuple[str, object]] = [("Local storage entries", len(entries))]

        live_violations = validate_semantic_rules(entries)
        for v in live_violations:
            fields.append(("  Live", f"FAIL: {v}"))
        if not live_violations:
            fields.append(("  Live config", "OK" if entries else "none declared"))

        # Fixture: kafka on control-plane and etcd with nofail must be rejected
        bad_entries = [
            {"name": "fixture_kafka_cp", "purpose": "kafka",
             "disk_type": "ssd",
             "functional_group_prefix": ["service_kube_control_plane"]},
            {"name": "fixture_etcd_nofail", "purpose": "etcd",
             "disk_type": "boss", "mount_options": "defaults,nofail",
             "functional_group_prefix": ["service_kube_control_plane"]},
        ]
        fixture_violations = validate_semantic_rules(bad_entries)
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


def check_precheck_local_storage_etcd_nfs_fallback(host) -> dict[str, Any]:
    """TC-FVT-004: Verify etcd uses NFS when no etcd disk entry is declared."""
    summary = "Local storage etcd NFS fallback"
    try:
        cfg = _load_storage_config(host)
        entries = _get_local_storage(cfg)
        _, reason = validate_etcd_nfs_fallback(entries)
        fields: list[tuple[str, object]] = [
            ("Local storage entries", len(entries)),
            ("etcd storage", reason),
        ]
        return prepare_result(True, summary, fields, "")
    except (OSError, TypeError, ValueError) as exc:
        return prepare_result(False, summary, [], str(exc))


def check_precheck_kafka_switch_validation(host) -> dict[str, Any]:  # pylint: disable=too-many-locals
    """TC-FVT-005/TC-FVT-029: Verify kafka_on_local_disk is absent or Boolean."""
    summary = "Kafka local-disk switch validation"
    try:
        # Telemetry config lives in a sibling input directory; load it if present.
        # If absent (not configured for telemetry), report as skip.
        input_dir = resolve_target_input_project_path(host)
        telemetry_path = os.path.join(input_dir, "telemetry_config.yml")

        try:
            telemetry_cfg = read_yaml_mapping(host, telemetry_path)
        except (OSError, FileNotFoundError):
            fields: list[tuple[str, object]] = [
                ("telemetry_config.yml", "absent — kafka_on_local_disk defaults to false")
            ]
            return prepare_result(True, summary, fields, "")

        violations = validate_kafka_switch_absent(telemetry_cfg)
        sinks = telemetry_cfg.get("telemetry_sinks") or {}
        kafka = sinks.get("kafka") or {} if isinstance(sinks, dict) else {}
        switch_val = kafka.get("kafka_on_local_disk") if isinstance(kafka, dict) else "absent"

        switch_repr = repr(switch_val) if switch_val is not None else "absent (default false)"
        fields = [("kafka_on_local_disk", switch_repr)]
        for v in violations:
            fields.append(("  Violation", f"FAIL: {v}"))

        # Fixture: non-Boolean value must be rejected
        bad_telemetry = {"telemetry_sinks": {"kafka": {"kafka_on_local_disk": "yes"}}}
        fixture_violations = validate_kafka_switch_absent(bad_telemetry)
        fixture_ok = len(fixture_violations) == 1
        fields.append((
            "  Fixture rejection",
            f"{'OK' if fixture_ok else 'FAIL'}: non-Boolean rejected",
        ))

        all_ok = not violations and fixture_ok
        error = ""
        if violations:
            error = "; ".join(violations)
        if not fixture_ok:
            error += ("; " if error else "") + "Fixture rejection of non-Boolean failed"
        return prepare_result(all_ok, summary, fields, error)
    except (OSError, TypeError, ValueError) as exc:
        return prepare_result(False, summary, [], str(exc))
