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

"""Shared helpers for PXE boot and post-boot workload verification."""

import json
import os
import re
import time
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Any

from omnia_auto import read_remote_env, run_on_host, run_ssh_command

from ..vars.pxeboot_vars import (
    CATALOG_ROLE_PREFIXES,
    ENV_CATALOG_FILE_PATH,
    KUBERNETES_CONTROL_PLANE_PREFIX,
    KUBERNETES_PRIMARY_CONTROL_PLANE_PREFIX,
    OMNIA_CONFIG,
    PXEBOOT_COMMANDS,
    PXEBOOT_STATUS,
    STORAGE_CONFIG,
)
from ._prepare_helpers import read_yaml_mapping
from ._provision_helpers import load_context


def runtime_result(
    success: bool,
    summary: str,
    fields: list[tuple[str, object]],
    error: str = "",
    *,
    skipped: bool = False,
) -> dict[str, Any]:
    """Return the stable result contract consumed by runtime tests."""
    return {
        "success": success,
        "skipped": skipped,
        "details": {"summary": summary, "fields": fields},
        "error": error,
    }


def runtime_exception(summary: str, exc: Exception) -> dict[str, Any]:
    """Convert a boundary exception into one safe failed result."""
    return runtime_result(False, summary, [], str(exc))


def load_runtime_context(host) -> dict[str, Any]:
    """Load desired nodes and the latest PXE status."""
    context = load_context(host)
    context["pxeboot_status"] = read_yaml_mapping(
        host,
        os.path.join(context["output_dir"], PXEBOOT_STATUS),
    )
    return context


def _catalog_feature_tokens(
    catalog: Mapping[str, Any],
    rows: list[dict[str, str]],
) -> set[str]:
    """Return names and components reachable from mapped functional layers."""
    layers = catalog.get("functionallayer", [])
    groups = catalog.get("groups", {})
    if not isinstance(layers, list) or not isinstance(groups, dict):
        raise TypeError("Catalog functional layers or groups are invalid")
    desired_roles = set()
    for row in rows:
        name = str(row.get("EXPECTED_FUNCTIONAL_GROUP") or "").lower()
        name = name.replace(
            KUBERNETES_PRIMARY_CONTROL_PLANE_PREFIX,
            KUBERNETES_CONTROL_PLANE_PREFIX,
        )
        desired_roles.update(
            prefix for prefix in CATALOG_ROLE_PREFIXES if name.startswith(prefix)
        )
    tokens: set[str] = set()
    for layer in layers:
        if not isinstance(layer, dict):
            continue
        name = str(layer.get("name") or "").lower()
        if not any(name.startswith(prefix) for prefix in desired_roles):
            continue
        tokens.add(name)
        components = layer.get("components", [])
        if not isinstance(components, list):
            raise TypeError(f"Catalog layer {name} components must be a list")
        for group_name in map(str, components):
            tokens.add(group_name.lower())
            group = groups.get(group_name, {})
            if not isinstance(group, dict):
                continue
            tokens.add(str(group.get("name") or "").lower())
            packages = group.get("components", [])
            if isinstance(packages, list):
                tokens.update(str(package).lower() for package in packages)
    return tokens


def load_workload_context(
    host,
    mapped_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Add workload inputs and catalog features to a mapped runtime context."""
    context = dict(mapped_context) if mapped_context is not None else load_context(host)
    input_dir = os.path.dirname(context["mapping_path"])
    context["omnia_config"] = read_yaml_mapping(
        host,
        os.path.join(input_dir, OMNIA_CONFIG),
    )
    context["storage_config"] = read_yaml_mapping(
        host,
        os.path.join(input_dir, STORAGE_CONFIG),
    )
    context["high_availability_config"] = read_yaml_mapping(
        host,
        os.path.join(input_dir, "high_availability_config.yml"),
    )
    orchestrator_config = read_yaml_mapping(
        host,
        os.path.join(input_dir, "orchestrator_config.yml"),
    )
    context["orchestrator_config"] = orchestrator_config
    context["network_spec"] = read_yaml_mapping(
        host,
        os.path.join(input_dir, "network_spec.yml"),
    )
    catalog_path = str(
        read_remote_env(host, ENV_CATALOG_FILE_PATH, required=False)
        or orchestrator_config.get("catalog_file_path")
        or ""
    )
    if not catalog_path:
        raise ValueError(
            f"{ENV_CATALOG_FILE_PATH} is not configured in the target "
            "Omnia environment or orchestrator_config.yml"
        )
    catalog_document = read_yaml_mapping(host, catalog_path)
    catalog = catalog_document.get("catalog", {})
    if not isinstance(catalog, dict) or not isinstance(catalog.get("groups"), dict):
        raise TypeError(f"Catalog groups are invalid in {catalog_path}")
    feature_tokens = _catalog_feature_tokens(catalog, context["rows"])
    context["features"] = {
        "openldap": any("openldap" in token for token in feature_tokens),
        "openmpi": any("openmpi" in token for token in feature_tokens),
        "ucx": any("ucx" in token for token in feature_tokens),
        "gpu": any(
            marker in token
            for token in feature_tokens
            for marker in ("cuda", "nvidia", "dcgm")
        ),
    }
    return context


def rows_matching(
    context: Mapping[str, Any],
    prefixes: tuple[str, ...],
) -> list[dict[str, str]]:
    """Return desired rows whose effective role has one allowed prefix."""
    return [
        row
        for row in context["rows"]
        if str(row.get("EXPECTED_FUNCTIONAL_GROUP", "")).startswith(prefixes)
    ]


def first_row(
    rows: list[dict[str, str]],
    prefix: str,
) -> dict[str, str] | None:
    """Return the first row for an effective functional-group prefix."""
    return next(
        (row for row in rows if row["EXPECTED_FUNCTIONAL_GROUP"].startswith(prefix)),
        None,
    )


def group_fields(
    rows: list[dict[str, str]],
    outcomes: Mapping[str, tuple[bool, str]],
) -> list[tuple[str, object]]:
    """Format node outcomes by effective functional group."""
    fields: list[tuple[str, object]] = []
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["EXPECTED_FUNCTIONAL_GROUP"], []).append(row)
    for group_name, group_rows in sorted(grouped.items()):
        passed = sum(outcomes[row["HOSTNAME"]][0] for row in group_rows)
        fields.append(
            ("Functional group", f"[{group_name}] ({passed}/{len(group_rows)})")
        )
        for row in group_rows:
            ok, detail = outcomes[row["HOSTNAME"]]
            fields.append(
                (
                    f"  {row['HOSTNAME']}",
                    f"{'✓' if ok else '✗'} {row['ADMIN_IP']} | {detail}",
                )
            )
    return fields


def retry_nodes(
    rows: list[dict[str, str]],
    probe: Callable[[dict[str, str]], tuple[bool, str]],
    retries: int,
    delay_seconds: int,
) -> dict[str, tuple[bool, str]]:
    """Retry only failed nodes and return the final per-host result."""
    pending = {row["HOSTNAME"]: row for row in rows}
    outcomes: dict[str, tuple[bool, str]] = {}
    for attempt in range(1, retries + 1):
        for hostname, row in list(pending.items()):
            ok, detail = probe(row)
            outcomes[hostname] = (ok, detail)
            if ok:
                pending.pop(hostname)
        if not pending or attempt == retries:
            break
        time.sleep(delay_seconds)
    return outcomes


def ping_probe(host, row: Mapping[str, str]) -> tuple[bool, str]:
    """Ping one administrative address from the execution OIM."""
    result = run_on_host(host, PXEBOOT_COMMANDS["ping"], row["ADMIN_IP"])
    detail = "ICMP reachable" if result.rc == 0 else "no ICMP response"
    return result.rc == 0, detail


def ssh_probe(host, row: Mapping[str, str]) -> tuple[bool, str]:
    """Check passwordless root SSH from the execution OIM."""
    result = run_ssh_command(
        host,
        row["ADMIN_IP"],
        PXEBOOT_COMMANDS["ssh_probe"],
    )
    detail = "passwordless root SSH" if result.rc == 0 else _safe_error(result)
    return result.rc == 0, detail


def hostname_ssh_probe(host, row: Mapping[str, str]) -> tuple[bool, str]:
    """Resolve a mapped hostname on the OIM and connect to that exact name."""
    resolution = run_on_host(
        host,
        PXEBOOT_COMMANDS["hostname_resolution"],
        row["HOSTNAME"],
    )
    addresses = {
        line.split()[0] for line in resolution.stdout.splitlines() if line.split()
    }
    ssh = run_ssh_command(host, row["HOSTNAME"], PXEBOOT_COMMANDS["ssh_probe"])
    valid_dns = resolution.rc == 0 and row["ADMIN_IP"] in addresses
    valid = valid_dns and ssh.rc == 0
    return (
        valid,
        (
            f"DNS={'valid' if valid_dns else 'invalid'} | "
            f"SSH={'passed' if ssh.rc == 0 else 'failed'}"
        ),
    )


def remote_command(host, row: Mapping[str, str], command: str):
    """Execute a fixed command on a desired node from the execution OIM."""
    return run_ssh_command(host, row["ADMIN_IP"], command)


def remote_json(host, row: Mapping[str, str], command: str) -> Any:
    """Run one fixed node command and parse its JSON response."""
    result = remote_command(host, row, command)
    if result.rc != 0:
        raise RuntimeError(_safe_error(result))
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{row['HOSTNAME']} returned invalid JSON") from exc


def direct_cloud_init_probe(host, row: Mapping[str, str]) -> tuple[bool, str]:
    """Return strict direct cloud-init state without relying on a run report."""
    command = remote_command(host, row, PXEBOOT_COMMANDS["cloud_init"])
    status_text, separator, json_text = command.stdout.partition("\n---JSON---\n")
    if not separator:
        return False, (
            "cloud-init did not return structured status: " + _safe_error(command)
        )
    try:
        payload = json.loads(json_text)
    except json.JSONDecodeError:
        return False, "cloud-init returned invalid JSON status"
    if not isinstance(payload, dict):
        return False, "cloud-init JSON status is not a mapping"
    state_match = re.search(r"^status:\s*(\S+)", status_text, re.MULTILINE)
    extended_match = re.search(r"^extended_status:\s*(\S+)", status_text, re.MULTILINE)
    state = str(
        payload.get("status") or (state_match.group(1) if state_match else "unknown")
    ).lower()
    extended = str(
        payload.get("extended_status")
        or (extended_match.group(1) if extended_match else state)
    ).lower()
    errors = payload.get("errors") or []
    recoverable = payload.get("recoverable_errors") or {}
    recoverable_messages = (
        [
            str(message).lower()
            for entries in recoverable.values()
            for message in (entries if isinstance(entries, list) else [entries])
        ]
        if isinstance(recoverable, dict)
        else []
    )
    benign_degraded = (
        state == "done"
        and extended.startswith("degraded")
        and not errors
        and bool(recoverable_messages)
        and all("empty cloud config" in message for message in recoverable_messages)
    )
    if state != "done":
        return False, f"cloud-init status={state}, extended={extended}"
    if errors:
        return False, f"cloud-init reported {len(errors)} error(s)"
    if extended.startswith("degraded") and not benign_degraded:
        return False, f"cloud-init extended_status={extended}"
    suffix = " (known empty-cloud-config warning)" if benign_degraded else ""
    return True, f"cloud-init done{suffix}"


def wait_for_cloud_init(
    host,
    row: Mapping[str, str],
    timeout_seconds: int,
    poll_seconds: int,
) -> tuple[bool, str]:
    """Poll strict direct cloud-init state until it is complete or times out."""
    started = time.monotonic()
    deadline = started + timeout_seconds
    detail = "cloud-init was not checked"
    attempt = 0
    while time.monotonic() < deadline:
        attempt += 1
        try:
            complete, detail = direct_cloud_init_probe(host, row)
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            detail = str(exc)[:300]
            complete = False
        if complete:
            return True, detail
        report_poll_progress(
            f"{row['HOSTNAME']} cloud-init",
            attempt,
            started,
            timeout_seconds,
            detail,
        )
        time.sleep(poll_seconds)
    return False, detail


def _safe_error(result) -> str:
    """Return a bounded command failure without leaking command content."""
    detail = (result.stderr or result.stdout or f"command rc={result.rc}").strip()
    return re.sub(r"\s+", " ", detail)[:300]


def selected_kubernetes_config(context: Mapping[str, Any]) -> dict[str, Any]:
    """Return the single Kubernetes deployment configuration."""
    entries = context["omnia_config"].get("service_k8s_cluster", [])
    if not isinstance(entries, list):
        raise TypeError("service_k8s_cluster must be a list")
    selected = [
        item
        for item in entries
        if isinstance(item, dict) and bool(item.get("deployment", False))
    ]
    if len(selected) != 1:
        raise ValueError(
            "Exactly one service_k8s_cluster entry must have deployment: true"
        )
    return selected[0]


def selected_slurm_config(context: Mapping[str, Any]) -> dict[str, Any]:
    """Return the single supported Slurm cluster configuration."""
    entries = context["omnia_config"].get("slurm_cluster", [])
    if not isinstance(entries, list) or len(entries) != 1:
        raise ValueError("Exactly one slurm_cluster entry is required")
    if not isinstance(entries[0], dict):
        raise TypeError("slurm_cluster entry must be a mapping")
    return entries[0]


def marker_is_authorized(marker: str) -> bool:
    """Return whether pytest explicitly selected a mutation marker."""
    active = {
        value.strip()
        for value in os.environ.get("OMNIA_FVT_AUTHORIZED_MARKERS", "").split(",")
        if value.strip()
    }
    return marker in active


def report_poll_progress(
    label: str,
    attempt: int,
    started: float,
    timeout_seconds: int,
    detail: str = "",
) -> None:
    """Render one bounded progress line for a retrying long operation."""
    elapsed = max(0, int(time.monotonic() - started))
    remaining = max(0, timeout_seconds - elapsed)
    suffix = f" | last state: {detail[:120]}" if detail else ""
    message = (
        f"    ↻ {label}: still in progress; retrying status check "
        f"(attempt {attempt}, elapsed {elapsed}s, remaining {remaining}s){suffix}"
    )
    # INFO logging is intentionally hidden in normal validation runs. Long-running
    # pull/reboot polls must remain visible so the operator can distinguish active
    # progress from a hung test.
    print(message, flush=True)


def run_remote_with_progress(
    host,
    row: Mapping[str, str],
    command: str,
    label: str,
    timeout_seconds: int,
    poll_seconds: int,
):
    """Run one bounded remote command while reporting progress periodically."""
    started = time.monotonic()
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(remote_command, host, row, command)
    attempt = 0
    try:
        while True:
            remaining = timeout_seconds - (time.monotonic() - started)
            if remaining <= 0:
                future.cancel()
                raise TimeoutError(f"{label} exceeded {timeout_seconds} seconds")
            try:
                result = future.result(timeout=min(poll_seconds, remaining))
                elapsed = int(time.monotonic() - started)
                print(f"    ✓ {label}: completed after {elapsed}s", flush=True)
                return result
            except FutureTimeoutError:
                attempt += 1
                report_poll_progress(
                    label,
                    attempt,
                    started,
                    timeout_seconds,
                )
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def wait_for_remote_command(
    host,
    row: Mapping[str, str],
    command: str,
    timeout_seconds: int,
    poll_seconds: int,
) -> tuple[bool, str]:
    """Poll one fixed remote command until it succeeds or times out."""
    started = time.monotonic()
    deadline = started + timeout_seconds
    detail = "command did not run"
    attempt = 0
    while time.monotonic() < deadline:
        attempt += 1
        try:
            result = remote_command(host, row, command)
        except (OSError, RuntimeError, ValueError) as exc:
            detail = str(exc)[:300]
            report_poll_progress(
                "Remote readiness check",
                attempt,
                started,
                timeout_seconds,
                detail,
            )
            time.sleep(poll_seconds)
            continue
        detail = _safe_error(result) if result.rc != 0 else result.stdout.strip()
        if result.rc == 0:
            return True, detail
        report_poll_progress(
            "Remote readiness check",
            attempt,
            started,
            timeout_seconds,
            detail,
        )
        time.sleep(poll_seconds)
    return False, detail
