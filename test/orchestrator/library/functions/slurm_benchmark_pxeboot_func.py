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

"""Real benchmark downloads through the deployed script in owned workspaces."""

import json
import re
import secrets
import shlex
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from omnia_auto import load_test_config

from ..vars.slurm_benchmark_vars import (
    BENCHMARK_BARRIER_TIMEOUT_SECONDS,
    BENCHMARK_COMMANDS,
    BENCHMARK_DOWNLOAD_TIMEOUT_SECONDS,
    BENCHMARK_LOCK_TIMEOUT_SECONDS,
    BENCHMARK_SNAPSHOT_SCRIPT,
    BENCHMARK_TOOLS,
    BENCHMARK_TOOLS_ROOT,
    BENCHMARK_WORKSPACE_PATTERN,
)
from ._pxeboot_helpers import marker_is_authorized, remote_command, runtime_result
from ._workload_helpers import optional_skip, slurm_compute_rows, slurm_context

_WORKSPACE = re.compile(BENCHMARK_WORKSPACE_PATTERN)
_ERRORS = (OSError, RuntimeError, TypeError, ValueError)


def _run(host, row, script):
    result = remote_command(
        host, row, BENCHMARK_COMMANDS["shell"].format(script=shlex.quote(script))
    )
    if result.rc:
        diagnostic = "\n".join(
            text.strip()[-1500:]
            for text in (result.stdout, result.stderr)
            if text and text.strip()
        )
        raise RuntimeError(
            f"{row['HOSTNAME']}: command failed (rc={result.rc}): "
            + (diagnostic or "no command output")
        )
    return result.stdout


def _storage(context, config):
    name = str(config.get("vast_storage_name") or "").strip()
    name = name or str(config.get("nfs_storage_name") or "").strip()
    matches = [
        entry
        for entry in context["storage_config"]["mounts"]
        if entry.get("name") == name
    ]
    if len(matches) != 1:
        raise ValueError("Benchmark storage must resolve to one configured mount")
    source, mount = matches[0]["source"], matches[0]["mount_point"].rstrip("/")
    if not source or not mount.startswith("/") or mount == "/":
        raise ValueError("Invalid benchmark storage source or mount point")
    return source, mount


def _validate_mount(output, source, mount):
    lines = output.strip().splitlines()
    if len(lines) != 2:
        raise ValueError("MOUNT FAILED: incomplete benchmark mount probe")
    parent, bound = (line.split() for line in lines)
    if parent not in ([source, "nfs", mount], [source, "nfs4", mount]):
        raise ValueError(
            f"MOUNT FAILED: expected NFS export {source} mounted exactly at {mount}; "
            f"actual: {lines[0]}"
        )
    if (
        len(bound) != 3
        or bound[1] not in {"nfs", "nfs4"}
        or bound[2] != BENCHMARK_TOOLS_ROOT
    ):
        raise ValueError(
            "MOUNT FAILED: /hpc_tools must be an exact NFS-backed mount point; "
            f"actual: {lines[1]}"
        )


def _parse_probe(output, source, mount):
    lines = output.strip().splitlines()
    if len(lines) != 4:
        raise ValueError("Incomplete benchmark mount/platform probe")
    _validate_mount("\n".join(lines[:2]), source, mount)
    platform = lines[2].split("|")
    if (
        len(platform) != 3
        or not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", platform[0])
        or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)*", platform[1])
        or platform[2] not in {"x86_64", "aarch64"}
    ):
        raise ValueError("Invalid detected benchmark platform")
    tools = tuple(lines[3].split())
    if set(tools) != set(BENCHMARK_TOOLS) or len(tools) != len(BENCHMARK_TOOLS):
        raise ValueError("Deployed benchmark_tools.list differs from supported tools")
    return tuple(platform)


def _probe(host, row, source, mount):
    expected = shlex.quote(mount + "/slurm/hpc_tools")
    script = BENCHMARK_COMMANDS["mount_probe"].format(
        expected=expected, mount=shlex.quote(mount)
    )
    mounts = _run(host, row, script)
    _validate_mount(mounts, source, mount)
    _run(host, row, BENCHMARK_COMMANDS["script_probe"].format())
    platform = _run(host, row, BENCHMARK_COMMANDS["probe"].format())
    return _parse_probe(mounts.rstrip() + "\n" + platform, source, mount)


def _preconditions(host):
    context, rows, _control, config = slurm_context(host)
    computes = slurm_compute_rows(rows)
    if not computes:
        return [], {}, []
    source, mount = _storage(context, config)
    records, fields, failures = {}, [], []
    for row in computes:
        try:
            records[row["HOSTNAME"]] = _probe(host, row, source, mount)
            fields.extend(
                [
                    (
                        f"{row['HOSTNAME']} mount",
                        f"PASS | {source} at {mount}; "
                        "slurm/hpc_tools bound to /hpc_tools",
                    ),
                    (
                        f"{row['HOSTNAME']} pull_benchmarks.sh",
                        "PRESENT | /hpc_tools/scripts/pull_benchmarks.sh | "
                        "executable | bash syntax passed",
                    ),
                ]
            )
        except _ERRORS as exc:
            failures.append(f"{row['HOSTNAME']}: {exc}")
    if failures:
        raise RuntimeError("Benchmark prerequisites failed: " + "; ".join(failures))
    return computes, records, fields


def check_slurm_benchmark_prerequisites(host):
    """Check the script and exact configured shared mount before any pull."""
    summary = "Slurm benchmark script and shared mount"
    try:
        computes, _records, fields = _preconditions(host)
        if not computes:
            return optional_skip(summary, "No Slurm compute nodes are mapped")
        return runtime_result(True, summary, fields)
    except _ERRORS as exc:
        return runtime_result(False, summary, [], str(exc))


def _validate_workspace(workspace):
    if not _WORKSPACE.fullmatch(workspace):
        raise ValueError("Refusing an unsafe benchmark FVT workspace")


def _prepare(host, row, workspace):
    _validate_workspace(workspace)
    # Reject an old deployment before invoking it with an isolated destination.
    script = BENCHMARK_COMMANDS["prepare"].format(workspace=workspace)
    _run(host, row, script)


def _applicable(platform):
    return tuple(
        tool
        for tool in BENCHMARK_TOOLS
        if tool != "msr-safe" or platform[2] == "x86_64"
    )


def _pull(host, row, workspace, label, barrier=False):
    _validate_workspace(workspace)
    wait = ""
    if barrier:
        wait = BENCHMARK_COMMANDS["barrier"].format(
            workspace=workspace,
            label=label,
            barrier_timeout=BENCHMARK_BARRIER_TIMEOUT_SECONDS,
        )
    return _run(
        host,
        row,
        BENCHMARK_COMMANDS["pull"].format(
            wait=wait,
            workspace=workspace,
            label=label,
            download_timeout=BENCHMARK_DOWNLOAD_TIMEOUT_SECONDS,
            lock_timeout=BENCHMARK_LOCK_TIMEOUT_SECONDS,
        ),
    )


def _snapshot(host, row, workspace, platform):
    directory = workspace + "/platforms/" + "/".join(platform)
    args = " ".join(shlex.quote(arg) for arg in (directory, *_applicable(platform)))
    output = _run(
        host,
        row,
        BENCHMARK_COMMANDS["snapshot"].format(
            script=shlex.quote(BENCHMARK_SNAPSHOT_SCRIPT), args=args
        ),
    )
    result = json.loads(output)
    if not isinstance(result, dict) or not result:
        raise ValueError("Empty benchmark archive snapshot")
    return result


def _archive_presence_fields(workspace, platform, snapshot):
    platform_name = "/".join(platform)
    return [
        (
            f"Archive presence ({platform_name})",
            f"PRESENT | {workspace}/platforms/{platform_name}/{archive}"
            f" | {metadata[1]} bytes | tar integrity passed",
        )
        for archive, metadata in sorted(snapshot.items())
    ]


def _idempotency(host, rows, records, workspace, fields):
    representatives = {}
    for row in rows:
        representatives.setdefault(records[row["HOSTNAME"]], row)
    for index, (platform, row) in enumerate(sorted(representatives.items())):
        first_count = _pull(host, row, workspace, f"{index}-first").count(
            "[INFO] Pulling from Pulp mirror..."
        )
        before = _snapshot(host, row, workspace, platform)
        fields.extend(_archive_presence_fields(workspace, platform, before))
        second_count = _pull(host, row, workspace, f"{index}-second").count(
            "[INFO] Pulling from Pulp mirror..."
        )
        after = _snapshot(host, row, workspace, platform)
        count = len(_applicable(platform))
        reasons = []
        if first_count != count:
            reasons.append(f"initial downloads: expected {count}, actual {first_count}")
        if second_count:
            reasons.append(f"rerun downloads: expected 0, actual {second_count}")
        reasons.extend(_snapshot_differences(before, after))
        if reasons:
            raise RuntimeError(
                f"Download/idempotency failed on {row['HOSTNAME']} "
                f"for {'/'.join(platform)} in {workspace}: " + "; ".join(reasons)
            )
        fields.append(
            (
                "/".join(platform),
                f"{count} tools; {len(before)} valid archives; "
                "rerun: zero downloads, checksums/sizes/mtime unchanged",
            )
        )


def _snapshot_differences(expected, actual):
    """Describe missing/added archives and the exact metadata that differs."""
    differences = []
    for path in sorted(expected.keys() - actual.keys()):
        differences.append(f"archive missing: {path}")
    for path in sorted(actual.keys() - expected.keys()):
        differences.append(f"unexpected archive: {path}")
    for path in sorted(expected.keys() & actual.keys()):
        for index, label in enumerate(("SHA-256", "size (bytes)", "mtime (ns)")):
            if expected[path][index] != actual[path][index]:
                differences.append(
                    f"{path}: {label} changed; expected {expected[path][index]}, "
                    f"actual {actual[path][index]}"
                )
    return differences


def _pair(rows, records):
    groups = {}
    for row in rows:
        key = (row["EXPECTED_FUNCTIONAL_GROUP"], records[row["HOSTNAME"]])
        groups.setdefault(key, []).append(row)
    return next((group[:2] for group in groups.values() if len(group) >= 2), [])


def _concurrency(host, rows, records, workspace, fields):
    platform = records[rows[0]["HOSTNAME"]]
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(_pull, host, row, workspace, f"peer-{i}", True)
            for i, row in enumerate(rows)
        ]
        outputs = [future.result() for future in futures]
    states = [_snapshot(host, row, workspace, platform) for row in rows]
    counts = [output.count("[INFO] Pulling from Pulp mirror...") for output in outputs]
    expected_count = len(_applicable(platform))
    reasons = []
    if sorted(counts) != [0, expected_count]:
        reasons.append(
            f"expected one node to download {expected_count} tools and the other 0; "
            f"actual: {rows[0]['HOSTNAME']}={counts[0]}, "
            f"{rows[1]['HOSTNAME']}={counts[1]}"
        )
    reasons.extend(_snapshot_differences(states[0], states[1]))
    if reasons:
        raise RuntimeError(
            f"Concurrent nodes did not reuse one shared download for {'/'.join(platform)} "
            f"in {workspace} (expected={rows[0]['HOSTNAME']}, "
            f"actual={rows[1]['HOSTNAME']}): " + "; ".join(reasons)
        )
    fields.append(
        ("Concurrent downloads", f"{counts}; both nodes see identical archives")
    )


def _finish(host, row, workspace, config, fields):
    """Persist logs before removing only this invocation's tools and workspace."""
    _validate_workspace(workspace)
    report = Path(config["report_path"]).expanduser().resolve() / "benchmarks"
    report.mkdir(parents=True, exist_ok=True)
    log = report / (workspace.rsplit("/", 1)[1] + ".log")
    output = _run(
        host,
        row,
        BENCHMARK_COMMANDS["logs"].format(workspace=workspace),
    )
    log.write_text(output, encoding="utf-8")
    fields.append(("Download logs", str(log)))
    if config.get("cleanup_benchmark_tools", True):
        _run(
            host,
            row,
            BENCHMARK_COMMANDS["cleanup"].format(workspace=workspace),
        )
        fields.append(("Benchmark tools cleanup", "Test downloads removed"))
    else:
        fields.append(("Retained benchmark tools", workspace))


def _download_check(host, concurrent=False):
    summary = "Slurm benchmark " + (
        "concurrent download" if concurrent else "download and idempotency"
    )
    if not (marker_is_authorized("functional") and marker_is_authorized("benchmark")):
        return optional_skip(summary, "Select benchmark for real downloads")
    fields, errors = [], []
    workspace, cleanup_row = "", None
    config = load_test_config()
    try:
        if not isinstance(config.get("cleanup_benchmark_tools", True), bool):
            raise ValueError("cleanup_benchmark_tools must be true or false")
        if (
            not isinstance(config.get("report_path"), str)
            or not config["report_path"].strip()
        ):
            raise ValueError("report_path is required to preserve download logs")
        rows, records, _fields = _preconditions(host)
        if not rows:
            return optional_skip(summary, "No Slurm compute nodes are mapped")
        if concurrent:
            rows = _pair(rows, records)
            if not rows:
                return optional_skip(
                    summary, "Need two same-platform computes in one functional group"
                )
        workspace = (
            BENCHMARK_TOOLS_ROOT + "/.omnia_fvt/benchmark-" + secrets.token_hex(8)
        )
        cleanup_row = rows[0]
        fields.append(("Test workspace", workspace))
        _prepare(host, cleanup_row, workspace)
        operation = _concurrency if concurrent else _idempotency
        operation(host, rows, records, workspace, fields)
    except _ERRORS as exc:
        errors.append(str(exc))
    finally:
        if workspace and cleanup_row is not None:
            try:
                _finish(host, cleanup_row, workspace, config, fields)
            except _ERRORS as exc:
                errors.append(
                    f"Log preservation/cleanup failed; inspect {workspace}: {exc}"
                )
    return runtime_result(not errors, summary, fields, "; ".join(errors))


def check_slurm_benchmark_idempotency(host):
    """Download every supported tool, validate archives, and rerun unchanged."""
    return _download_check(host)


def check_slurm_benchmark_concurrency(host):
    """Start two deployed script copies together on shared storage."""
    return _download_check(host, concurrent=True)
