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

"""HPC benchmarks staging, contracts, and invariance checks after PXE.

All checks are aligned to the actual deployed staging pipeline in
``omnia/src/orchestrator/roles/slurm_config`` — namely
``pull_benchmarks.sh.j2`` and ``benchmark_tools.list.j2`` — not to the
legacy ``files/pull_benchmarks.sh`` that ships in the source tree but is
never installed at runtime.
"""

import time

from ..vars.pxeboot_vars import (
    HPC_BENCHMARKS_MSR_SAFE_PACKAGE,
    HPC_BENCHMARKS_PULL_SCRIPT,
    HPC_BENCHMARKS_RHEL_MAJOR,
    HPC_BENCHMARKS_STAGING_TIMEOUT_SECONDS,
    HPC_BENCHMARKS_TOOLS_LIST,
    HPC_TOOLS_BASE,
    HPC_TOOLS_CONTAINER_IMAGES_DIRECTORY,
    HPC_TOOLS_CORE_SUBDIRS,
    HPC_TOOLS_CUDA_DIRECTORY,
    HPC_TOOLS_DIRECTORY_MODE,
    HPC_TOOLS_NVIDIA_SDK_DIRECTORY,
    HPC_TOOLS_SCRIPTS_DIRECTORY,
    PXEBOOT_COMMANDS,
)
from ._hpc_benchmarks_helpers import (
    command_error,
    compute_architectures,
    core_directory_records,
    computes_or_skip,
    egress_probe,
    enforce_mode_755,
    expected_tools_for_arch,
    hpc_benchmarks_context,
    list_directory,
    list_tool_files,
    parse_staging_report,
    pull_script_exists,
    pull_script_forbids_build,
    pulp_directory_has_files,
    pulp_tarball_directory,
    read_benchmark_tools_list,
    read_directory_stat,
    read_pull_script_var,
    rhel_version,
    run_pull_script,
    scan_for_binaries,
    snapshot_directories,
    source_only_scan_paths,
    staged_tool_directories,
    tools_list_deployed,
)
from ._pxeboot_helpers import (
    remote_command,
    runtime_exception,
    runtime_result,
)
from ._workload_helpers import optional_skip


# ---------------------------------------------------------------------------
# TC-01: BENCHMARK TOOL DECLARATION
# ---------------------------------------------------------------------------
def check_hpc_benchmarks_json_declaration(host):
    """Verify benchmark_tools.list is deployed and lists at least one tool.

    2.3 replaces the 2.2 slurm_custom.json parse with a compute-side read of
    ``/hpc_tools/scripts/benchmark_tools.list`` — the source of truth the
    deployed ``pull_benchmarks.sh`` actually consumes.
    """
    summary = "HPC benchmarks tool declaration"
    try:
        _context, _control, computes, skipped = computes_or_skip(host, summary)
        if skipped:
            return skipped
        row = computes[0]
        if not tools_list_deployed(host, row):
            return runtime_result(
                False,
                summary,
                [("Expected list", HPC_BENCHMARKS_TOOLS_LIST)],
                "benchmark_tools.list is not deployed",
            )
        tools = read_benchmark_tools_list(host, row)
        arch_map = compute_architectures(host, computes)
        fields: list[tuple[str, object]] = [
            ("benchmark_tools.list", HPC_BENCHMARKS_TOOLS_LIST),
            ("Declared tools", ", ".join(tools) or "none"),
        ]
        failures: list[str] = []
        for arch in sorted(set(arch_map.values())):
            expected = expected_tools_for_arch(tools, arch)
            fields.append((f"tools[{arch}]", f"count={len(expected)}"))
            if not expected:
                failures.append(f"no tools staged for {arch}")
        if not tools:
            failures.append("benchmark_tools.list is empty")
        return runtime_result(
            not failures,
            summary,
            fields,
            "; ".join(failures) if failures else "",
        )
    except FileNotFoundError as exc:
        return optional_skip(summary, str(exc))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


# ---------------------------------------------------------------------------
# TC-02: PULP OFFLINE REPO SYNC (compute-side HTTP probe)
# ---------------------------------------------------------------------------
def check_hpc_benchmarks_local_repo_sync(host):
    """Verify each declared tool has a non-empty Pulp tarball directory.

    Replays the exact Pulp URL the deployed ``pull_benchmarks.sh`` builds
    (``https://${PULP_SERVER}/pulp/content/offline_repo/cluster/${ARCH}/
    rhel/${OS_VERSION}/tarball/${tool}/``) and requires at least one file
    entry per tool. This is the fidelity check for ``local_repo.yml``
    having synchronized the tarballs into Pulp.
    """
    summary = "HPC benchmarks local repo sync"
    try:
        _context, _control, computes, skipped = computes_or_skip(host, summary)
        if skipped:
            return skipped
        row = computes[0]
        if not tools_list_deployed(host, row):
            return optional_skip(summary, "benchmark_tools.list is not deployed")
        tools = read_benchmark_tools_list(host, row)
        pulp_server = read_pull_script_var(host, row, "PULP_SERVER")
        os_version = read_pull_script_var(host, row, "OS_VERSION")
        if not pulp_server or not os_version:
            return runtime_result(
                False,
                summary,
                [
                    ("PULP_SERVER", pulp_server or "<unset>"),
                    ("OS_VERSION", os_version or "<unset>"),
                ],
                "Cannot extract PULP_SERVER/OS_VERSION from pull_benchmarks.sh",
            )
        arch_map = compute_architectures(host, computes)
        fields: list[tuple[str, object]] = [
            ("Pulp server", pulp_server),
            ("OS version", os_version),
        ]
        missing: list[str] = []
        for arch in sorted(set(arch_map.values())):
            resolved = 0
            expected = expected_tools_for_arch(tools, arch)
            for tool in expected:
                url = pulp_tarball_directory(pulp_server, os_version, arch, tool)
                present, _count = pulp_directory_has_files(host, row, url)
                if present:
                    resolved += 1
                else:
                    missing.append(f"{arch}/{tool}")
            fields.append((f"pulp[{arch}]", f"resolved={resolved}/{len(expected)}"))
        if missing:
            fields.append(("missing", ", ".join(missing[:10])))
        return runtime_result(
            not missing,
            summary,
            fields,
            f"Missing Pulp tarballs: {len(missing)}" if missing else "",
        )
    except FileNotFoundError as exc:
        return optional_skip(summary, str(exc))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


# ---------------------------------------------------------------------------
# TC-03: /hpc_tools LAYOUT
# ---------------------------------------------------------------------------
def check_hpc_benchmarks_tools_dir_creation(host):
    """Verify /hpc_tools and required subdirectories exist with mode 0755."""
    summary = "HPC benchmarks /hpc_tools layout"
    try:
        _context, _control, computes, skipped = computes_or_skip(host, summary)
        if skipped:
            return skipped
        fields: list[tuple[str, object]] = [
            ("Required subdirectories", ", ".join(HPC_TOOLS_CORE_SUBDIRS)),
            ("Expected mode", HPC_TOOLS_DIRECTORY_MODE),
        ]
        failures: list[str] = []
        for row in computes:
            root = read_directory_stat(host, row, HPC_TOOLS_BASE)
            root_ok = enforce_mode_755(root)
            sub_status: list[str] = []
            for name, record in core_directory_records(host, row):
                ok = enforce_mode_755(record)
                sub_status.append(f"{name}={'ok' if ok else 'bad'}")
                if not ok:
                    failures.append(f"{row['HOSTNAME']}:{name}")
            fields.append(
                (
                    f"  {row['HOSTNAME']}",
                    f"root={'ok' if root_ok else 'bad'} | " + ", ".join(sub_status),
                )
            )
            if not root_ok:
                failures.append(f"{row['HOSTNAME']}:{HPC_TOOLS_BASE}")
        return runtime_result(
            not failures,
            summary,
            fields,
            f"{len(failures)} directory issue(s): {', '.join(failures[:6])}"
            if failures
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


# ---------------------------------------------------------------------------
# TC-04: ARTIFACT STAGING (post-run)
# ---------------------------------------------------------------------------
def check_hpc_benchmarks_artifact_copy(host):
    """Verify each declared tool has a non-empty ``/hpc_tools/<tool>`` dir.

    ``hpc_tools.yml`` only deploys ``pull_benchmarks.sh``; artifacts are
    populated when the operator runs it. When no tool subdirectories exist
    yet the test skips with a ``staging not yet executed`` reason rather
    than reporting a false failure.
    """
    summary = "HPC benchmarks artifact staging"
    try:
        _context, _control, computes, skipped = computes_or_skip(host, summary)
        if skipped:
            return skipped
        row = computes[0]
        if not tools_list_deployed(host, row):
            return optional_skip(summary, "benchmark_tools.list is not deployed")
        tools = read_benchmark_tools_list(host, row)
        if not staged_tool_directories(host, row):
            return optional_skip(
                summary,
                "Staging not yet executed — no tool directories in /hpc_tools",
            )
        arch_map = compute_architectures(host, computes)
        expected: set[str] = set()
        for arch in set(arch_map.values()):
            expected.update(expected_tools_for_arch(tools, arch))
        fields: list[tuple[str, object]] = [
            ("Declared tools", ", ".join(sorted(expected)))
        ]
        missing: list[str] = []
        for tool in sorted(expected):
            base = f"{HPC_TOOLS_BASE}/{tool}"
            record = read_directory_stat(host, row, base)
            if not record["present"]:
                missing.append(tool)
                fields.append((f"  {tool}", "directory absent"))
                continue
            files = list_tool_files(host, row, base)
            non_empty = [entry for entry in files if entry["type"] == "f" and entry["size"] > 0]
            if not non_empty:
                missing.append(tool)
            fields.append(
                (f"  {tool}", f"files={len(files)} | non_empty={len(non_empty)}")
            )
        return runtime_result(
            not missing,
            summary,
            fields,
            f"Missing artifacts: {', '.join(missing)}" if missing else "",
        )
    except FileNotFoundError as exc:
        return optional_skip(summary, str(exc))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


# ---------------------------------------------------------------------------
# TC-05: msr-safe ARCHITECTURE BOUNDARY
# ---------------------------------------------------------------------------
def check_hpc_benchmarks_msr_safe_arch_boundary(host):
    """Verify msr-safe is declared and honoured only on x86_64 nodes.

    The deployed ``pull_benchmarks.sh`` hard-codes
    ``if [[ "$tool" == "msr-safe" && "$ARCH" != "x86_64" ]]; then [WARN] Skipping``.
    This check asserts:

    * ``msr-safe`` is present in ``benchmark_tools.list`` (else the boundary
      is vacuous)
    * On x86_64 nodes, the tool is either not yet staged (skip) or a
      populated directory exists
    * On aarch64 nodes, ``/hpc_tools/msr-safe`` never exists
    """
    summary = "HPC benchmarks msr-safe arch boundary"
    try:
        _context, _control, computes, skipped = computes_or_skip(host, summary)
        if skipped:
            return skipped
        row = computes[0]
        if not tools_list_deployed(host, row):
            return optional_skip(summary, "benchmark_tools.list is not deployed")
        tools = read_benchmark_tools_list(host, row)
        declared = HPC_BENCHMARKS_MSR_SAFE_PACKAGE in tools
        arch_map = compute_architectures(host, computes)
        fields: list[tuple[str, object]] = [
            ("Package", HPC_BENCHMARKS_MSR_SAFE_PACKAGE),
            ("Declared in benchmark_tools.list", declared),
        ]
        if not declared:
            return runtime_result(
                False,
                summary,
                fields,
                f"{HPC_BENCHMARKS_MSR_SAFE_PACKAGE} not declared in benchmark_tools.list",
            )
        violations: list[str] = []
        x86_staged = False
        for host_name, arch in sorted(arch_map.items()):
            row_for = next(item for item in computes if item["HOSTNAME"] == host_name)
            base = f"{HPC_TOOLS_BASE}/{HPC_BENCHMARKS_MSR_SAFE_PACKAGE}"
            record = read_directory_stat(host, row_for, base)
            present = record["present"]
            fields.append(
                (f"  {host_name} ({arch})", "present" if present else "absent")
            )
            if arch == "aarch64" and present:
                violations.append(f"{host_name}: msr-safe staged on aarch64")
            if arch == "x86_64" and present:
                x86_staged = True
            if arch == "x86_64" and not present:
                violations.append(
                    f"{host_name}: msr-safe declared but not staged on x86_64"
                )
        return runtime_result(
            not violations,
            summary,
            fields,
            "; ".join(violations) if violations else "",
        )
    except FileNotFoundError as exc:
        return optional_skip(summary, str(exc))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


# ---------------------------------------------------------------------------
# TC-06: DEPLOYMENT CONTRACT (narrowed)
# ---------------------------------------------------------------------------
def check_hpc_benchmarks_container_first_guidance(host):
    """Verify ``pull_benchmarks.sh`` and ``benchmark_tools.list`` are deployed.

    The 2.2 container-first guidance test (HPL / HPL-MxP / STREAM declared
    as ``image`` type in ``slurm_custom.json``, with the canonical
    ``nvcr.io/nvidia/hpc-benchmarks`` marker) is not currently reflected
    anywhere in ``omnia/src/orchestrator/roles/slurm_config``. Until that
    pipeline ships, this TC is narrowed to the deployment contract that
    ``hpc_tools.yml`` actually enforces: both artifacts installed under
    ``/hpc_tools/scripts`` with the documented permissions.
    """
    summary = "HPC benchmarks staging artifacts deployed"
    try:
        _context, _control, computes, skipped = computes_or_skip(host, summary)
        if skipped:
            return skipped
        fields: list[tuple[str, object]] = [
            ("Staging script", HPC_BENCHMARKS_PULL_SCRIPT),
            ("Tools list", HPC_BENCHMARKS_TOOLS_LIST),
        ]
        failures: list[str] = []
        for row in computes:
            script_ok, markers = pull_script_exists(host, row)
            list_ok = tools_list_deployed(host, row)
            fields.append(
                (
                    f"  {row['HOSTNAME']}",
                    (
                        f"script={'ok' if script_ok else 'missing'} "
                        f"(markers={markers}) | "
                        f"list={'ok' if list_ok else 'missing'}"
                    ),
                )
            )
            if not script_ok:
                failures.append(f"{row['HOSTNAME']}: script missing")
            if not list_ok:
                failures.append(f"{row['HOSTNAME']}: list missing")
        return runtime_result(
            not failures,
            summary,
            fields,
            "; ".join(failures) if failures else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


# ---------------------------------------------------------------------------
# TC-07: SOURCE-ONLY DELIVERY
# ---------------------------------------------------------------------------
def check_hpc_benchmarks_source_only_delivery(host):
    """Verify no compile commands ship with the script or the staged artifacts.

    Scans only benchmark tool subdirectories — the framework-owned dirs
    (cuda, nvidia_sdk, container_images, scripts) are excluded because
    they legitimately contain third-party binaries.
    """
    summary = "HPC benchmarks source-only delivery"
    try:
        _context, _control, computes, skipped = computes_or_skip(host, summary)
        if skipped:
            return skipped
        fields: list[tuple[str, object]] = [
            ("Staging script", HPC_BENCHMARKS_PULL_SCRIPT),
            ("Excluded from scan", "cuda, nvidia_sdk, container_images, scripts"),
        ]
        violations: list[str] = []
        for row in computes:
            script_ok, _markers = pull_script_exists(host, row)
            if not script_ok:
                fields.append((f"  {row['HOSTNAME']}", "script missing"))
                violations.append(f"{row['HOSTNAME']}: pull_benchmarks.sh missing")
                continue
            no_build = pull_script_forbids_build(host, row)
            scan_paths = source_only_scan_paths(host, row)
            binaries = scan_for_binaries(host, row, scan_paths) if scan_paths else []
            fields.append(
                (
                    f"  {row['HOSTNAME']}",
                    (
                        f"no_build={no_build} scanned_dirs={len(scan_paths)} "
                        f"suspicious_binaries={len(binaries)}"
                    ),
                )
            )
            if not no_build:
                violations.append(f"{row['HOSTNAME']}: compile keywords in script")
            if binaries:
                violations.append(
                    f"{row['HOSTNAME']}: {len(binaries)} pre-compiled binary(s)"
                )
        return runtime_result(
            not violations,
            summary,
            fields,
            "; ".join(violations[:6]) if violations else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


# ---------------------------------------------------------------------------
# TC-08: PER-TOOL STAGING REPORT (destructive)
# ---------------------------------------------------------------------------
def check_hpc_benchmarks_per_tool_staging_report(host):
    """Rerun pull_benchmarks.sh and verify the per-tool report is well-formed.

    The deployed script emits ``[SUCCESS]``, ``[WARN]``, ``[ERROR]`` markers
    followed by a summary of the form
    ``[INFO] Successful: N | Skipped: N | Failed: N``. The parser prefers
    the summary counts and falls back to marker counts.
    """
    summary = "HPC benchmarks per-tool staging report"
    try:
        _context, _control, computes, skipped = computes_or_skip(host, summary)
        if skipped:
            return skipped
        row = computes[0]
        script_ok, _markers = pull_script_exists(host, row)
        if not script_ok:
            return runtime_result(
                False,
                summary,
                [("Staging script", HPC_BENCHMARKS_PULL_SCRIPT)],
                "pull_benchmarks.sh is not deployed",
            )
        result = run_pull_script(host, row, HPC_BENCHMARKS_STAGING_TIMEOUT_SECONDS)
        report = parse_staging_report(result.stdout)
        totalled = report["success"] + report["skipped"] + report["failed"]
        ok = (
            result.rc == 0
            and totalled > 0
            and report["failed"] == 0
        )
        fields = [
            ("Execution node", f"{row['HOSTNAME']} | {row['ADMIN_IP']}"),
            ("Staging exit code", result.rc),
            ("Total tools processed", report["total"]),
            ("Successful", report["success"]),
            ("Skipped", report["skipped"]),
            ("[WARN] lines", report["warn"]),
            ("Failed", report["failed"]),
        ]
        return runtime_result(
            ok,
            summary,
            fields,
            command_error(result) if not ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


# ---------------------------------------------------------------------------
# TC-09: END-TO-END PROVISIONING (composite)
# ---------------------------------------------------------------------------
def check_hpc_benchmarks_e2e_provisioning(host):
    """Combine tool-declaration, offline sync, layout, artifacts, and NFS.

    Mandatory stages (tool_list, tools_dirs, artifacts, nfs) must not be
    skipped.  A skipped mandatory stage is treated as a failure to prevent
    false-green results when prerequisites are missing.
    """
    summary = "HPC benchmarks end-to-end provisioning"
    _MANDATORY_STAGES = {"tool_list", "tools_dirs", "artifacts", "nfs"}
    try:
        results = {
            "tool_list": check_hpc_benchmarks_json_declaration(host),
            "pulp_sync": check_hpc_benchmarks_local_repo_sync(host),
            "tools_dirs": check_hpc_benchmarks_tools_dir_creation(host),
            "artifacts": check_hpc_benchmarks_artifact_copy(host),
            "nfs": check_hpc_benchmarks_nfs_accessibility(host),
        }
        fields = [
            (
                stage,
                (
                    "skipped"
                    if outcome.get("skipped")
                    else ("ok" if outcome.get("success") else "failed")
                ),
            )
            for stage, outcome in results.items()
        ]
        failures = [
            stage
            for stage, outcome in results.items()
            if not outcome.get("skipped") and not outcome.get("success")
        ]
        # Mandatory stages must not be skipped in an E2E check
        skipped_mandatory = [
            stage
            for stage, outcome in results.items()
            if stage in _MANDATORY_STAGES and outcome.get("skipped")
        ]
        if skipped_mandatory:
            failures.extend(
                f"{stage} (mandatory stage was skipped)"
                for stage in skipped_mandatory
            )
        return runtime_result(
            not failures,
            summary,
            fields,
            f"Failed stages: {', '.join(failures)}" if failures else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


# ---------------------------------------------------------------------------
# TC-10: NFS ACCESSIBILITY
# ---------------------------------------------------------------------------
def check_hpc_benchmarks_nfs_accessibility(host):
    """Verify /hpc_tools is mounted and readable on every compute node."""
    summary = "HPC benchmarks /hpc_tools NFS accessibility"
    try:
        _context, _control, computes, skipped = computes_or_skip(host, summary)
        if skipped:
            return skipped
        fields: list[tuple[str, object]] = [("Mount", HPC_TOOLS_BASE)]
        failures: list[str] = []
        for row in computes:
            mount = remote_command(host, row, PXEBOOT_COMMANDS["hpc_tools_findmnt"])
            mount_ok = mount.rc == 0 and HPC_TOOLS_BASE in mount.stdout
            readable = remote_command(
                host, row, PXEBOOT_COMMANDS["hpc_tools_readable"] % HPC_TOOLS_BASE
            )
            readable_ok = readable.rc == 0
            fields.append(
                (
                    f"  {row['HOSTNAME']}",
                    (
                        f"mount={'ok' if mount_ok else 'missing'} | "
                        f"readable={'ok' if readable_ok else 'no'}"
                    ),
                )
            )
            if not (mount_ok and readable_ok):
                failures.append(row["HOSTNAME"])
        return runtime_result(
            not failures,
            summary,
            fields,
            f"NFS unavailable on: {', '.join(failures)}" if failures else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


# ---------------------------------------------------------------------------
# TC-11: AIR-GAPPED STAGING (destructive)
# ---------------------------------------------------------------------------
def check_hpc_benchmarks_airgapped_staging(host):
    """Verify egress probe confirms air-gap, then staging still succeeds via Pulp."""
    summary = "HPC benchmarks air-gapped staging"
    try:
        _context, _control, computes, skipped = computes_or_skip(host, summary)
        if skipped:
            return skipped
        row = computes[0]
        egress_open, egress_detail = egress_probe(host, row)
        fields: list[tuple[str, object]] = [
            ("Execution node", f"{row['HOSTNAME']} | {row['ADMIN_IP']}"),
            ("Egress probe", egress_detail),
        ]
        if egress_open:
            return runtime_result(
                False,
                summary,
                fields,
                "External egress is reachable; the cluster is not air-gapped",
            )
        result = run_pull_script(host, row, HPC_BENCHMARKS_STAGING_TIMEOUT_SECONDS)
        report = parse_staging_report(result.stdout)
        fields.extend(
            [
                ("Staging exit code", result.rc),
                ("Successful", report["success"]),
                ("Skipped", report["skipped"]),
                ("Failed", report["failed"]),
            ]
        )
        ok = result.rc == 0 and report["failed"] == 0
        return runtime_result(
            ok,
            summary,
            fields,
            command_error(result) if not ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


# ---------------------------------------------------------------------------
# TC-12: POST-STAGING VALIDATION
# ---------------------------------------------------------------------------
def check_hpc_benchmarks_post_staging_validation(host):
    """Verify tool subdirectories are present per benchmark_tools.list.

    Uses the same "staging not yet executed" skip contract as TC-04.
    """
    summary = "HPC benchmarks post-staging validation"
    try:
        _context, _control, computes, skipped = computes_or_skip(host, summary)
        if skipped:
            return skipped
        row = computes[0]
        if not tools_list_deployed(host, row):
            return optional_skip(summary, "benchmark_tools.list is not deployed")
        tools = read_benchmark_tools_list(host, row)
        if not staged_tool_directories(host, row):
            return optional_skip(
                summary,
                "Staging not yet executed — no tool directories in /hpc_tools",
            )
        arch_map = compute_architectures(host, computes)
        fields: list[tuple[str, object]] = [
            ("Declared tools", ", ".join(tools) or "none")
        ]
        missing: list[str] = []
        for compute in computes:
            arch = arch_map[compute["HOSTNAME"]]
            expected = expected_tools_for_arch(tools, arch)
            per_host: list[str] = []
            for tool in expected:
                base = f"{HPC_TOOLS_BASE}/{tool}"
                record = read_directory_stat(host, compute, base)
                if not record["present"]:
                    per_host.append(tool)
                    missing.append(f"{compute['HOSTNAME']}:{tool}")
            fields.append(
                (
                    f"  {compute['HOSTNAME']} ({arch})",
                    f"missing={len(per_host)}"
                    + (f" ({', '.join(per_host[:5])})" if per_host else ""),
                )
            )
        return runtime_result(
            not missing,
            summary,
            fields,
            f"{len(missing)} missing tool dir(s)" if missing else "",
        )
    except FileNotFoundError as exc:
        return optional_skip(summary, str(exc))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


# ---------------------------------------------------------------------------
# TC-13: RHEL COMPATIBILITY
# ---------------------------------------------------------------------------
def check_hpc_benchmarks_rhel_compatibility(host):
    """Verify every compute node runs the RHEL major this suite targets."""
    summary = "HPC benchmarks RHEL compatibility"
    try:
        _context, _control, computes, skipped = computes_or_skip(host, summary)
        if skipped:
            return skipped
        fields: list[tuple[str, object]] = [
            ("Expected RHEL major", HPC_BENCHMARKS_RHEL_MAJOR)
        ]
        failures: list[str] = []
        for row in computes:
            version = rhel_version(host, row)
            major = version.split(".", 1)[0]
            ok = major == HPC_BENCHMARKS_RHEL_MAJOR
            fields.append((f"  {row['HOSTNAME']}", f"VERSION_ID={version}"))
            if not ok:
                failures.append(f"{row['HOSTNAME']} ({version})")
        return runtime_result(
            not failures,
            summary,
            fields,
            f"Unsupported RHEL version on: {', '.join(failures)}"
            if failures
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def _invariance_snapshot(host, row, path: str) -> tuple[dict, dict]:
    """Return (stat_record, immediate-listing) for a path."""
    return read_directory_stat(host, row, path), {
        entry["path"]: entry["mode"] for entry in list_directory(host, row, path)
    }


def _invariance_check(host, path: str, summary: str):
    """Shared before/after invariance harness across a staging run.

    Requires the staging script to exit successfully before comparing
    snapshots. A script that fails before changing anything must not
    produce a false 'unchanged' pass.
    """
    _context, _control, computes, skipped = computes_or_skip(host, summary)
    if skipped:
        return skipped
    fields: list[tuple[str, object]] = [("Path", path)]
    failures: list[str] = []
    touched = 0
    for row in computes:
        before_stat, before_children = _invariance_snapshot(host, row, path)
        if not before_stat["present"]:
            fields.append((f"  {row['HOSTNAME']}", "directory absent"))
            continue
        touched += 1
        staging_result = run_pull_script(host, row, HPC_BENCHMARKS_STAGING_TIMEOUT_SECONDS)
        if staging_result.rc != 0:
            failures.append(
                f"{row['HOSTNAME']}: staging script failed (rc={staging_result.rc})"
            )
            fields.append(
                (f"  {row['HOSTNAME']}", f"staging failed (rc={staging_result.rc})")
            )
            continue
        after_stat, after_children = _invariance_snapshot(host, row, path)
        unchanged = before_stat == after_stat and before_children == after_children
        fields.append(
            (
                f"  {row['HOSTNAME']}",
                (
                    f"children_before={len(before_children)} "
                    f"children_after={len(after_children)} "
                    f"unchanged={unchanged}"
                ),
            )
        )
        if not unchanged:
            failures.append(row["HOSTNAME"])
    if touched == 0:
        return optional_skip(summary, f"{path} is not deployed on any compute node")
    return runtime_result(
        not failures,
        summary,
        fields,
        f"{path} changed on: {', '.join(failures)}" if failures else "",
    )


# ---------------------------------------------------------------------------
# TC-14: CUDA INVARIANCE
# ---------------------------------------------------------------------------
def check_hpc_benchmarks_cuda_flow_unaffected(host):
    """Verify /hpc_tools/cuda is present and unchanged after staging."""
    summary = "HPC benchmarks CUDA flow invariance"
    try:
        return _invariance_check(host, HPC_TOOLS_CUDA_DIRECTORY, summary)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


# ---------------------------------------------------------------------------
# TC-15: NVIDIA SDK INVARIANCE
# ---------------------------------------------------------------------------
def check_hpc_benchmarks_nvhpc_flow_unaffected(host):
    """Verify /hpc_tools/nvidia_sdk is present and unchanged after staging."""
    summary = "HPC benchmarks NVIDIA SDK invariance"
    try:
        return _invariance_check(host, HPC_TOOLS_NVIDIA_SDK_DIRECTORY, summary)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


# ---------------------------------------------------------------------------
# TC-16: CONTAINER IMAGE INVARIANCE
# ---------------------------------------------------------------------------
def check_hpc_benchmarks_container_image_unaffected(host):
    """Verify /hpc_tools/container_images is unchanged after staging."""
    summary = "HPC benchmarks container image invariance"
    try:
        return _invariance_check(
            host, HPC_TOOLS_CONTAINER_IMAGES_DIRECTORY, summary
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


# ---------------------------------------------------------------------------
# TC-17: OpenMPI / UCX INVARIANCE
# ---------------------------------------------------------------------------
def check_hpc_benchmarks_openmpi_unaffected(host):
    """Verify OpenMPI/UCX discovery output is stable across a staging run."""
    summary = "HPC benchmarks OpenMPI invariance"
    try:
        context, _rows, control, _computes, _config = hpc_benchmarks_context(host)
        if control is None:
            return optional_skip(summary, "No Slurm control node is mapped")
        if not context["features"].get("openmpi", False) \
                and not context["features"].get("ucx", False):
            return optional_skip(
                summary,
                "OpenMPI/UCX are not selected for this Slurm topology",
            )

        failures: list[str] = []

        openmpi_before = remote_command(
            host, control, PXEBOOT_COMMANDS["openmpi"],
        )
        ucx_before = remote_command(
            host, control, PXEBOOT_COMMANDS["ucx"],
        )
        if openmpi_before.rc != 0:
            failures.append(
                f"OpenMPI pre-probe failed: {command_error(openmpi_before)}"
            )
        if ucx_before.rc != 0:
            failures.append(
                f"UCX pre-probe failed: {command_error(ucx_before)}"
            )

        _ctx2, _ctrl2, computes, skipped = computes_or_skip(
            host, summary,
        )
        if skipped is None and computes:
            staging = run_pull_script(
                host, computes[0],
                HPC_BENCHMARKS_STAGING_TIMEOUT_SECONDS,
            )
            if staging.rc != 0:
                failures.append(
                    f"Staging failed (rc={staging.rc}): "
                    f"{command_error(staging)}"
                )
        time.sleep(1)

        openmpi_after = remote_command(
            host, control, PXEBOOT_COMMANDS["openmpi"],
        )
        ucx_after = remote_command(
            host, control, PXEBOOT_COMMANDS["ucx"],
        )
        if openmpi_after.rc != 0:
            failures.append(
                f"OpenMPI post-probe failed: "
                f"{command_error(openmpi_after)}"
            )
        if ucx_after.rc != 0:
            failures.append(
                f"UCX post-probe failed: {command_error(ucx_after)}"
            )

        openmpi_ok = (
            openmpi_before.rc == 0
            and openmpi_after.rc == 0
            and openmpi_before.stdout == openmpi_after.stdout
        )
        ucx_ok = (
            ucx_before.rc == 0
            and ucx_after.rc == 0
            and ucx_before.stdout == ucx_after.stdout
        )
        if not openmpi_ok and not any("OpenMPI" in f for f in failures):
            failures.append("OpenMPI discovery output drifted")
        if not ucx_ok and not any("UCX" in f for f in failures):
            failures.append("UCX discovery output drifted")

        fields = [
            ("Control node", control["HOSTNAME"]),
            ("OpenMPI unchanged", openmpi_ok),
            ("UCX unchanged", ucx_ok),
        ]
        return runtime_result(
            not failures,
            summary,
            fields,
            "; ".join(failures) if failures else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


# ---------------------------------------------------------------------------
# TC-18: EXISTING DIRS PRESERVED (destructive)
# ---------------------------------------------------------------------------
def check_hpc_benchmarks_existing_dirs_preserved(host):
    """Verify pre-existing /hpc_tools subdirectories survive a staging run."""
    summary = "HPC benchmarks existing directory preservation"
    try:
        _context, _control, computes, skipped = computes_or_skip(
            host, summary,
        )
        if skipped:
            return skipped
        fields: list[tuple[str, object]] = []
        failures: list[str] = []
        for row in computes:
            before = snapshot_directories(host, row)
            staging = run_pull_script(
                host, row, HPC_BENCHMARKS_STAGING_TIMEOUT_SECONDS,
            )
            if staging.rc != 0:
                failures.append(
                    f"{row['HOSTNAME']}: staging failed "
                    f"(rc={staging.rc}): "
                    f"{command_error(staging)}"
                )
                fields.append(
                    (f"  {row['HOSTNAME']}", f"✗ staging rc={staging.rc}"),
                )
                continue
            after = snapshot_directories(host, row)
            removed = tuple(
                name for name in before if name not in after
            )
            fields.append(
                (
                    f"  {row['HOSTNAME']}",
                    f"before={len(before)} after={len(after)} "
                    f"removed={len(removed)}",
                )
            )
            if removed:
                failures.append(
                    f"{row['HOSTNAME']}:{','.join(removed[:3])}"
                )
        return runtime_result(
            not failures,
            summary,
            fields,
            f"Pre-existing dirs removed: {', '.join(failures)}"
            if failures
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


# ---------------------------------------------------------------------------
# TC-19: STAGING IDEMPOTENCY (destructive)
# ---------------------------------------------------------------------------
def check_hpc_benchmarks_staging_idempotency(host):
    """Rerun the staging script and verify the directory snapshot is stable.

    The deployed script emits ``[WARN] $tool already present ... Skipping``
    per tool on a re-run — no ``[SUCCESS]`` markers. The check requires the
    summary's ``Successful`` count to be zero on the second run.
    """
    summary = "HPC benchmarks staging idempotency"
    try:
        _context, _control, computes, skipped = computes_or_skip(host, summary)
        if skipped:
            return skipped
        row = computes[0]
        before = snapshot_directories(host, row)
        first = run_pull_script(host, row, HPC_BENCHMARKS_STAGING_TIMEOUT_SECONDS)
        mid = snapshot_directories(host, row)
        second = run_pull_script(host, row, HPC_BENCHMARKS_STAGING_TIMEOUT_SECONDS)
        after = snapshot_directories(host, row)
        report = parse_staging_report(second.stdout)
        stable = before == mid == after
        no_downloads = report["success"] == 0
        ok = first.rc == 0 and second.rc == 0 and stable and no_downloads
        fields = [
            ("Execution node", f"{row['HOSTNAME']} | {row['ADMIN_IP']}"),
            ("Directory snapshot stable", stable),
            ("Second-run Successful", report["success"]),
            ("Second-run Skipped", report["skipped"]),
            ("Second-run Failed", report["failed"]),
        ]
        error = ""
        if not stable:
            error = "Directory listing drifted across staging runs"
        elif not no_downloads:
            error = "Second staging run reported new downloads"
        elif first.rc != 0 or second.rc != 0:
            error = command_error(second if second.rc != 0 else first)
        return runtime_result(ok, summary, fields, error)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
