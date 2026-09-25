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

"""Orchestrator performance, idempotency, and security contracts."""

import os
import re
from collections.abc import Callable
from typing import Any

from omnia_auto import load_test_config, run_on_host
from omnia_auto import run_playbook as _run_playbook

from ..vars.common_vars import PLAYBOOK_ENTRY_POINT, PLAYBOOK_WORKDIR
from ..vars.nft_vars import (
    ALLOWED_CREDENTIAL_MODES,
    NFT_LIFECYCLE_TAGS,
    NFT_THRESHOLD_CONFIG_KEY,
    NFT_TIMEOUT_GRACE_SECONDS,
    NON_PERSISTENT_CHANGE_TASK_PREFIXES,
    ORCHESTRATOR_CREDENTIAL_FILE,
    ORCHESTRATOR_LOG_DIRECTORY,
    ORCHESTRATOR_SSH_PRIVATE_KEY,
    ORCHESTRATOR_VAULT_KEY_FILE,
    REQUIRED_PRIVATE_KEY_MODE,
    VAULT_HEADER_PATTERN,
)
from ..vars.prepare_vars import OPENCHAMI_CONTAINERS
from .cleanup_func import (
    check_cleanup_artifacts,
    check_cleanup_credentials,
    check_cleanup_kubernetes,
    check_cleanup_openchami,
    check_cleanup_openldap,
    check_cleanup_slurm,
    cleanup_extra_vars,
)
from .openchami_prepare_func import (
    check_prepare_openchami_apis,
    check_prepare_openchami_artifacts,
    check_prepare_openchami_containers,
    check_prepare_openchami_services,
    check_prepare_openchami_storage,
)
from .postgres_prepare_func import check_prepare_postgresql_readiness
from .project_func import resolve_target_input_project_path


def _result(
    success: bool,
    summary: str,
    fields: list[tuple[str, object]],
    error: str = "",
) -> dict[str, Any]:
    """Return one structured NFT result."""
    return {
        "success": success,
        "details": summary,
        "fields": fields,
        "error": error,
    }


def resolve_nft_thresholds(config: dict[str, Any] | None = None) -> dict[str, int]:
    """Validate and return lifecycle performance thresholds in seconds."""
    source = dict(config if config is not None else load_test_config())
    thresholds = source.get(NFT_THRESHOLD_CONFIG_KEY)
    if not isinstance(thresholds, dict):
        raise TypeError(f"{NFT_THRESHOLD_CONFIG_KEY} must be a mapping")

    unknown = sorted(set(thresholds) - set(NFT_LIFECYCLE_TAGS))
    missing = sorted(set(NFT_LIFECYCLE_TAGS) - set(thresholds))
    if unknown or missing:
        issues = []
        if missing:
            issues.append("missing: " + ", ".join(missing))
        if unknown:
            issues.append("unknown: " + ", ".join(unknown))
        raise ValueError(f"Invalid {NFT_THRESHOLD_CONFIG_KEY} ({'; '.join(issues)})")

    resolved: dict[str, int] = {}
    for lifecycle in NFT_LIFECYCLE_TAGS:
        value = thresholds[lifecycle]
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise TypeError(
                f"{NFT_THRESHOLD_CONFIG_KEY}.{lifecycle} must be a positive integer"
            )
        resolved[lifecycle] = value
    return resolved


def persistent_changed_count(output: str) -> int:
    """Count recap changes except documented in-memory inventory updates."""
    recap_counts = [int(value) for value in re.findall(r"\bchanged=(\d+)\b", output)]
    if not recap_counts:
        raise ValueError("Ansible output contains no changed= recap")

    ignored = 0
    current_task = ""
    for line in output.splitlines():
        task_match = re.search(r"TASK \[(.+?)]", line)
        if task_match:
            current_task = task_match.group(1)
            continue
        if re.search(r"\bchanged: \[[^]]+]", line) and any(
            current_task.startswith(prefix)
            for prefix in NON_PERSISTENT_CHANGE_TASK_PREFIXES
        ):
            ignored += 1

    total = sum(recap_counts)
    if ignored > total:
        raise ValueError("Ignored change count exceeds Ansible recap changes")
    return total - ignored


def _playbook_failure(tag: str, result: dict[str, Any]) -> str:
    """Return a concise playbook failure suitable for reports."""
    raw = str(result.get("error") or "")
    rc = result.get("rc", "unknown")
    # Extract only the first meaningful line; drop generic HOW TO FIX blocks
    # that are aimed at interactive runner output, not test reports.
    if raw:
        first_line = raw.split("\n")[0].strip()
        return f"{tag} failed (rc={rc}): {first_line}"
    return f"{tag} exited with rc={rc}"


def _run_lifecycle(tag: str, **kwargs) -> dict[str, Any]:
    """Run one lifecycle through the canonical Orchestrator entry point."""
    return _run_playbook(
        playbook=PLAYBOOK_ENTRY_POINT,
        playbook_workdir=PLAYBOOK_WORKDIR,
        tag=tag,
        **kwargs,
    )


def check_lifecycle_performance(host, lifecycle: str) -> dict[str, Any]:
    """Run one lifecycle and enforce its configured duration contract."""
    del host
    try:
        threshold = resolve_nft_thresholds()[lifecycle]
        extra_vars = cleanup_extra_vars() if lifecycle == "cleanup" else None
    except (KeyError, TypeError, ValueError) as exc:
        return _result(False, "NFT configuration is invalid", [], str(exc))

    result = _run_lifecycle(
        lifecycle,
        extra_vars=extra_vars,
        timeout=threshold + NFT_TIMEOUT_GRACE_SECONDS,
    )
    duration = float(result.get("duration", 0.0))
    within = duration <= threshold
    fields = [
        ("Lifecycle", lifecycle),
        ("Return code", result.get("rc", "unknown")),
        ("Duration seconds", f"{duration:.1f}"),
        ("Threshold seconds", threshold),
        ("Threshold basis", "configured reference OIM and current project input"),
    ]
    failures = []
    if not result.get("success"):
        failures.append(_playbook_failure(lifecycle, result))
    if not within:
        failures.append(f"duration {duration:.1f}s exceeds {threshold}s")
    return _result(
        not failures,
        f"{lifecycle} lifecycle completed within its duration contract",
        fields,
        "; ".join(failures),
    )


def _container_identity_snapshot(host) -> tuple[dict[str, str], list[str]]:
    """Return stable OpenCHAMI container identity and runtime attributes."""
    identities: dict[str, str] = {}
    failures = []
    command = (
        "podman inspect --format "
        "'{{.Id}}|{{.Created}}|{{.State.StartedAt}}|{{.State.Status}}' "
        "%s 2>/dev/null"
    )
    for container in OPENCHAMI_CONTAINERS:
        probe = run_on_host(host, command, container)
        value = probe.stdout.strip() if probe.rc == 0 else ""
        parts = value.split("|")
        if len(parts) != 4 or parts[-1] != "running" or not parts[0]:
            failures.append(f"{container}: unavailable or not running")
            continue
        identities[container] = value
    return identities, failures


def _prepare_readiness(host) -> tuple[list[tuple[str, object]], list[str]]:
    """Reuse prepare FVT postconditions after an idempotent rerun."""
    checks: tuple[tuple[str, Callable], ...] = (
        ("Containers", check_prepare_openchami_containers),
        ("Services", check_prepare_openchami_services),
        ("Authenticated APIs", check_prepare_openchami_apis),
        ("Persistent storage and TLS", check_prepare_openchami_storage),
        ("Packages and configuration", check_prepare_openchami_artifacts),
        ("PostgreSQL and SMD database", check_prepare_postgresql_readiness),
    )
    fields = []
    failures = []
    for label, checker in checks:
        result = checker(host)
        fields.append((label, "passed" if result["success"] else "FAILED"))
        if not result["success"]:
            failures.append(f"{label}: {result['error']}")
    return fields, failures


def check_prepare_idempotency(host) -> dict[str, Any]:
    """Run prepare twice and prove a stable second execution."""
    first = _run_lifecycle("prepare")
    if not first.get("success"):
        return _result(
            False,
            "First prepare execution failed",
            [("First run return code", first.get("rc", "unknown"))],
            _playbook_failure("prepare", first),
        )
    before, snapshot_failures = _container_identity_snapshot(host)
    if snapshot_failures:
        return _result(
            False,
            "OpenCHAMI identity snapshot failed after first prepare",
            [("Container snapshot", "FAILED")],
            "; ".join(snapshot_failures),
        )

    second = _run_lifecycle("prepare")
    after, second_snapshot_failures = _container_identity_snapshot(host)
    try:
        changed = persistent_changed_count(str(second.get("output", "")))
    except ValueError as exc:
        changed = -1
        second_snapshot_failures.append(str(exc))

    recreated = sorted(
        container
        for container in OPENCHAMI_CONTAINERS
        if before.get(container) != after.get(container)
    )
    readiness_fields, readiness_failures = _prepare_readiness(host)
    failures = [*second_snapshot_failures, *readiness_failures]
    if not second.get("success"):
        failures.append(_playbook_failure("prepare", second))
    if changed != 0:
        failures.append(f"second prepare reported {changed} persistent changes")
    if recreated:
        failures.append("container identity changed: " + ", ".join(recreated))

    fields = [
        ("First run duration seconds", f"{float(first.get('duration', 0)):.1f}"),
        ("Second run duration seconds", f"{float(second.get('duration', 0)):.1f}"),
        ("Second run persistent changes", changed),
        (
            "Stable container identities",
            f"{len(after) - len(recreated)}/{len(OPENCHAMI_CONTAINERS)}",
        ),
        *readiness_fields,
    ]
    return _result(
        not failures,
        "Prepare rerun preserved runtime identity and readiness",
        fields,
        "; ".join(failures),
    )


def check_precheck_idempotency(host) -> dict[str, Any]:
    """Run precheck twice and require a read-only second execution."""
    del host
    first = _run_lifecycle("precheck")
    if not first.get("success"):
        return _result(
            False,
            "First precheck execution failed",
            [("First run return code", first.get("rc", "unknown"))],
            _playbook_failure("precheck", first),
        )
    second = _run_lifecycle("precheck")
    try:
        changed = persistent_changed_count(str(second.get("output", "")))
        parse_error = ""
    except ValueError as exc:
        changed = -1
        parse_error = str(exc)

    failures = []
    if not second.get("success"):
        failures.append(_playbook_failure("precheck", second))
    if parse_error:
        failures.append(parse_error)
    if changed != 0:
        failures.append(f"second precheck reported {changed} persistent changes")
    return _result(
        not failures,
        "Precheck rerun completed without persistent changes",
        [
            ("First run duration seconds", f"{float(first.get('duration', 0)):.1f}"),
            ("Second run duration seconds", f"{float(second.get('duration', 0)):.1f}"),
            ("Second run persistent changes", changed),
        ],
        "; ".join(failures),
    )


def _cleanup_postconditions(host) -> tuple[list[tuple[str, object]], list[str]]:
    """Reuse every full-cleanup FVT postcondition."""
    checks: tuple[tuple[str, Callable], ...] = (
        ("OpenCHAMI", check_cleanup_openchami),
        ("OpenLDAP", check_cleanup_openldap),
        ("Slurm", check_cleanup_slurm),
        ("Kubernetes", check_cleanup_kubernetes),
        ("Artifacts", check_cleanup_artifacts),
        ("Credentials", check_cleanup_credentials),
    )
    fields = []
    failures = []
    for label, checker in checks:
        result = checker(host)
        fields.append(
            (f"{label} postcondition", "passed" if result["success"] else "FAILED")
        )
        if not result["success"]:
            failures.append(f"{label}: {result['error']}")
    return fields, failures


def check_cleanup_idempotency(host) -> dict[str, Any]:
    """Run full cleanup twice and prove the second run is a no-op."""
    try:
        extra_vars = cleanup_extra_vars()
    except (TypeError, ValueError) as exc:
        return _result(False, "Cleanup configuration is invalid", [], str(exc))
    first = _run_lifecycle("cleanup", extra_vars=extra_vars)
    if not first.get("success"):
        return _result(
            False,
            "First cleanup execution failed",
            [("First run return code", first.get("rc", "unknown"))],
            _playbook_failure("cleanup", first),
        )
    second = _run_lifecycle("cleanup", extra_vars=extra_vars)
    try:
        changed = persistent_changed_count(str(second.get("output", "")))
        parse_error = ""
    except ValueError as exc:
        changed = -1
        parse_error = str(exc)

    postcondition_fields, postcondition_failures = _cleanup_postconditions(host)
    failures = [*postcondition_failures]
    if not second.get("success"):
        failures.append(_playbook_failure("cleanup", second))
    if parse_error:
        failures.append(parse_error)
    if changed != 0:
        failures.append(f"second cleanup reported {changed} persistent changes")
    return _result(
        not failures,
        "Cleanup rerun remained successful and fully removed state",
        [
            ("First run duration seconds", f"{float(first.get('duration', 0)):.1f}"),
            ("Second run duration seconds", f"{float(second.get('duration', 0)):.1f}"),
            ("Second run persistent changes", changed),
            *postcondition_fields,
        ],
        "; ".join(failures),
    )


def _stat_identity(host, path: str) -> tuple[str, str, str] | None:
    """Return mode, owner, and group for one target path."""
    probe = run_on_host(host, "stat -Lc '%%a|%%U|%%G' -- %s", path)
    if probe.rc != 0:
        return None
    parts = probe.stdout.strip().split("|", 2)
    if len(parts) != 3:
        return None
    return parts[0], parts[1], parts[2]


def check_credential_file_permissions(host) -> dict[str, Any]:
    """Require the encrypted product credential file to be access-restricted."""
    path = os.path.join(
        resolve_target_input_project_path(host), ORCHESTRATOR_CREDENTIAL_FILE
    )
    identity = _stat_identity(host, path)
    if identity is None:
        return _result(
            False,
            "Credential permission check failed",
            [("File", path)],
            "required credential file is missing",
        )
    mode, owner, group = identity
    success = mode in ALLOWED_CREDENTIAL_MODES and owner == "root"
    return _result(
        success,
        "Credential file access is restricted",
        [("File", path), ("Mode", mode), ("Owner", f"{owner}:{group}")],
        "expected root ownership and mode 0600 or 0640" if not success else "",
    )


def check_ssh_private_key_permissions(host) -> dict[str, Any]:
    """Require the deployed OIM private key to be root-owned mode 0600."""
    identity = _stat_identity(host, ORCHESTRATOR_SSH_PRIVATE_KEY)
    if identity is None:
        return _result(
            False,
            "SSH private-key permission check failed",
            [("File", ORCHESTRATOR_SSH_PRIVATE_KEY)],
            "required OIM private key is missing",
        )
    mode, owner, group = identity
    success = mode == REQUIRED_PRIVATE_KEY_MODE and owner == "root"
    return _result(
        success,
        "OIM SSH private key access is restricted",
        [
            ("File", ORCHESTRATOR_SSH_PRIVATE_KEY),
            ("Mode", mode),
            ("Owner", f"{owner}:{group}"),
        ],
        "expected root ownership and mode 0600" if not success else "",
    )


def _log_file_violations(lines: list[str]) -> list[str]:
    """Return unsafe or malformed records from a target log inventory."""
    violations = []
    for line in lines:
        parts = line.split("|", 3)
        if len(parts) != 4:
            violations.append("unparseable log inventory record")
            continue
        mode, owner, _group, path = parts
        try:
            world_bits = int(mode, 8) & 0o007
        except ValueError:
            violations.append(f"{path}: invalid mode {mode}")
            continue
        if owner != "root" or world_bits:
            violations.append(f"{path}: mode={mode}, owner={owner}")
    return violations


def check_log_file_permissions(host) -> dict[str, Any]:
    """Require Orchestrator logs to be root-owned and not world-exposed."""
    directory_identity = _stat_identity(host, ORCHESTRATOR_LOG_DIRECTORY)
    if directory_identity is None:
        return _result(
            False,
            "Log permission check failed",
            [("Directory", ORCHESTRATOR_LOG_DIRECTORY)],
            "required log directory is missing",
        )
    directory_mode, directory_owner, directory_group = directory_identity
    probe = run_on_host(
        host,
        "find %s -xdev -type f -printf '%%m|%%u|%%g|%%p\\n' 2>/dev/null",
        ORCHESTRATOR_LOG_DIRECTORY,
    )
    if probe.rc != 0:
        return _result(
            False,
            "Log permission check failed",
            [("Directory", ORCHESTRATOR_LOG_DIRECTORY)],
            f"log inventory failed with rc={probe.rc}",
        )

    files = [line for line in probe.stdout.splitlines() if line.strip()]
    violations = _log_file_violations(files)

    try:
        directory_world_writable = bool(int(directory_mode, 8) & 0o002)
    except ValueError:
        directory_world_writable = True
    if directory_owner != "root" or directory_world_writable:
        violations.append(
            f"{ORCHESTRATOR_LOG_DIRECTORY}: mode={directory_mode}, owner={directory_owner}"
        )
    if not files:
        violations.append("no Orchestrator log files were found")

    fields: list[tuple[str, object]] = [
        ("Directory", ORCHESTRATOR_LOG_DIRECTORY),
        ("Directory mode", directory_mode),
        ("Directory owner", f"{directory_owner}:{directory_group}"),
        ("Log files checked", len(files)),
        ("Permission violations", len(violations)),
    ]
    fields.extend(("Violation", item) for item in violations[:10])
    return _result(
        not violations,
        "Orchestrator logs are not world-exposed",
        fields,
        "; ".join(violations) if violations else "",
    )


def check_vault_encryption(host) -> dict[str, Any]:
    """Require an exact Ansible Vault header and protected local vault key."""
    input_path = resolve_target_input_project_path(host)
    credential_path = os.path.join(input_path, ORCHESTRATOR_CREDENTIAL_FILE)
    key_path = os.path.join(input_path, ORCHESTRATOR_VAULT_KEY_FILE)
    header_probe = run_on_host(host, "head -n 1 -- %s", credential_path)
    header = header_probe.stdout.strip() if header_probe.rc == 0 else ""
    header_ok = bool(re.fullmatch(VAULT_HEADER_PATTERN, header))
    key_identity = _stat_identity(host, key_path)
    key_ok = bool(
        key_identity
        and key_identity[0] == REQUIRED_PRIVATE_KEY_MODE
        and key_identity[1] == "root"
    )
    fields = [
        ("Credential file", credential_path),
        ("Vault header", "valid" if header_ok else "INVALID OR MISSING"),
        ("Vault key", key_path),
        ("Vault key mode", key_identity[0] if key_identity else "missing"),
        (
            "Vault key owner",
            f"{key_identity[1]}:{key_identity[2]}" if key_identity else "missing",
        ),
    ]
    failures = []
    if not header_ok:
        failures.append(
            "credential file does not have an exact supported Ansible Vault header"
        )
    if not key_ok:
        failures.append("vault key must exist, be root-owned, and use mode 0600")
    return _result(
        not failures,
        "Credential encryption and vault-key protection are valid",
        fields,
        "; ".join(failures),
    )


# -----------------------------------------------------------------
# Lifecycle — clean-baseline and fresh-install contracts
# -----------------------------------------------------------------


def _lifecycle_cleanup_postconditions(
    host,
) -> tuple[list[tuple[str, object]], list[str]]:
    """Reuse cleanup FVT postconditions, excluding credentials.

    The lifecycle baseline preserves credentials so the subsequent
    fresh-install can proceed without interactive prompts.
    """
    checks: tuple[tuple[str, Callable], ...] = (
        ("OpenCHAMI", check_cleanup_openchami),
        ("OpenLDAP", check_cleanup_openldap),
        ("Slurm", check_cleanup_slurm),
        ("Kubernetes", check_cleanup_kubernetes),
        ("Artifacts", check_cleanup_artifacts),
    )
    fields = []
    failures = []
    for label, checker in checks:
        result = checker(host)
        fields.append(
            (f"{label} postcondition", "passed" if result["success"] else "FAILED")
        )
        if not result["success"]:
            failures.append(f"{label}: {result['error']}")
    fields.append(("Credentials postcondition", "skipped (preserved for lifecycle)"))
    return fields, failures


def check_clean_baseline(host) -> dict[str, Any]:
    """Run cleanup and verify all postconditions to prove a clean OIM state.

    Credentials are preserved (``cleanup_credentials=false``) so the
    subsequent fresh-install lifecycle can run without interactive
    password prompts.
    """
    try:
        extra_vars = cleanup_extra_vars()
    except (TypeError, ValueError) as exc:
        return _result(False, "Cleanup configuration is invalid", [], str(exc))

    # Preserve credentials so prepare does not prompt for manual input.
    extra_vars["cleanup_credentials"] = "false"

    result = _run_lifecycle("cleanup", extra_vars=extra_vars)
    if not result.get("success"):
        return _result(
            False,
            "Baseline cleanup execution failed",
            [
                ("Lifecycle", "cleanup"),
                ("Return code", result.get("rc", "unknown")),
                ("Duration seconds", f"{float(result.get('duration', 0)):.1f}"),
            ],
            _playbook_failure("cleanup", result),
        )

    postcondition_fields, postcondition_failures = (
        _lifecycle_cleanup_postconditions(host)
    )
    fields = [
        ("Cleanup duration seconds", f"{float(result.get('duration', 0)):.1f}"),
        ("Credentials policy", "preserved for lifecycle"),
        *postcondition_fields,
    ]
    return _result(
        not postcondition_failures,
        "OIM baseline is clean — all cleanup postconditions passed",
        fields,
        "; ".join(postcondition_failures),
    )


def check_lifecycle_fresh_install(host) -> dict[str, Any]:
    """Run precheck, prepare, and provision from a proven-clean baseline."""
    lifecycles = ("precheck", "prepare", "provision")
    durations: dict[str, float] = {}
    for lifecycle in lifecycles:
        result = _run_lifecycle(lifecycle)
        durations[lifecycle] = float(result.get("duration", 0))
        if not result.get("success"):
            completed = [
                lc for lc in lifecycles if lc in durations and lc != lifecycle
            ]
            fields = [
                ("Failed lifecycle", lifecycle),
                ("Return code", result.get("rc", "unknown")),
                ("Completed phases", ", ".join(completed) if completed else "none"),
                *(
                    (f"{lc} duration seconds", f"{durations[lc]:.1f}")
                    for lc in lifecycles
                    if lc in durations
                ),
            ]
            return _result(
                False,
                f"Fresh install failed at {lifecycle} phase",
                fields,
                _playbook_failure(lifecycle, result),
            )

    # Verify prepare postconditions
    readiness_fields, readiness_failures = _prepare_readiness(host)

    # Verify provision postconditions by importing checkers directly
    from .smd_provision_func import check_smd_identity, check_smd_groups
    from .boot_service_provision_func import (
        check_boot_configurations,
        check_boot_nodes,
    )
    from .metadata_service_provision_func import (
        check_metadata_groups,
        check_metadata_instances,
    )

    provision_checks: tuple[tuple[str, Callable], ...] = (
        ("SMD identity", check_smd_identity),
        ("SMD functional groups", check_smd_groups),
        ("Boot configurations", check_boot_configurations),
        ("Boot node identity", check_boot_nodes),
        ("Metadata groups", check_metadata_groups),
        ("Metadata instances", check_metadata_instances),
    )
    provision_fields: list[tuple[str, object]] = []
    provision_failures: list[str] = []
    for label, checker in provision_checks:
        check_result = checker(host)
        provision_fields.append(
            (label, "passed" if check_result["success"] else "FAILED")
        )
        if not check_result["success"]:
            provision_failures.append(f"{label}: {check_result['error']}")

    all_failures = [*readiness_failures, *provision_failures]
    fields = [
        *(
            (f"{lc} duration seconds", f"{durations[lc]:.1f}")
            for lc in lifecycles
        ),
        *readiness_fields,
        *provision_fields,
    ]
    return _result(
        not all_failures,
        "Fresh-install lifecycle completed and all postconditions passed",
        fields,
        "; ".join(all_failures),
    )
