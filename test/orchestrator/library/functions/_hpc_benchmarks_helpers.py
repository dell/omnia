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

"""Private HPC-benchmarks context, discovery, and evaluation helpers.

Source-of-truth alignment with omnia/src/orchestrator/roles/slurm_config:

* ``pull_benchmarks.sh.j2`` (deployed) reads ``benchmark_tools.list`` line
  by line — not ``slurm_custom.json`` — and pulls from a Pulp HTTPS mirror.
* ``benchmark_tools.list.j2`` is one tool per line; ``msr-safe`` is x86_64
  only and the script itself emits ``[WARN] ... Skipping.`` on aarch64.
* The script emits ``[SUCCESS]``, ``[WARN]``, ``[ERROR]`` markers plus a
  trailing ``Successful: N / Skipped: N / Failed: N`` summary; it never
  emits ``[SKIP]`` or ``[FAIL]``.
* ``hpc_tools.yml`` creates ``/hpc_tools/{cuda,scripts,container_images,
  nvidia_sdk}`` with ``common_mode=0755`` and deploys the script + list.
* ``/hpc_tools`` is the compute-node NFS mount point; tool subdirectories
  are only populated once the operator runs the script manually.
"""

import re
import shlex
from typing import Any

from ..vars.pxeboot_vars import (
    HPC_BENCHMARKS_MSR_SAFE_PACKAGE,
    HPC_BENCHMARKS_PULL_SCRIPT,
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
from ._pxeboot_helpers import remote_command
from ._workload_helpers import (
    optional_skip,
    slurm_compute_rows,
    slurm_context,
)

_SUPPORTED_ARCHITECTURES: frozenset[str] = frozenset({"x86_64", "aarch64"})

# ``pull_benchmarks.sh.j2`` never touches these directories. Excluding them
# from the source-only executable scan prevents legitimate CUDA / NVHPC /
# container-image binaries from producing false positives.
_STAGING_EXCLUDED_SUBDIRS: frozenset[str] = frozenset(
    {"cuda", "nvidia_sdk", "container_images", "scripts"}
)


def hpc_benchmarks_context(host):
    """Return workload context, Slurm rows, controller, and compute rows."""
    context, rows, control, config = slurm_context(host)
    return context, rows, control, slurm_compute_rows(rows), config


def computes_or_skip(host, summary):
    """Return context+computes, or the canonical skip result when unmapped."""
    context, _rows, control, computes, _config = hpc_benchmarks_context(host)
    if not computes:
        return (
            context,
            control,
            computes,
            optional_skip(summary, "No Slurm compute nodes are mapped"),
        )
    return context, control, computes, None


def command_error(result) -> str:
    """Return a bounded command failure suitable for reports."""
    detail = (result.stderr or result.stdout or f"command rc={result.rc}").strip()
    return re.sub(r"\s+", " ", detail)[:300]


def detect_architecture(host, row) -> str:
    """Return the validated CPU architecture reported by one node."""
    result = remote_command(host, row, PXEBOOT_COMMANDS["arch"])
    if result.rc != 0:
        raise RuntimeError(command_error(result))
    arch = result.stdout.strip()
    if arch not in _SUPPORTED_ARCHITECTURES:
        raise ValueError(f"Unsupported architecture: {arch!r}")
    return arch


def compute_architectures(host, computes) -> dict[str, str]:
    """Return a HOSTNAME -> architecture map for the mapped compute nodes."""
    return {row["HOSTNAME"]: detect_architecture(host, row) for row in computes}


def read_benchmark_tools_list(host, row) -> list[str]:
    """Return the tool names declared in the deployed benchmark_tools.list.

    Mirrors the parsing rules in ``pull_benchmarks.sh.j2``: skip empty lines
    and lines starting with ``#``; trim whitespace; preserve order.
    """
    result = remote_command(
        host,
        row,
        PXEBOOT_COMMANDS["hpc_benchmarks_read_json"] % HPC_BENCHMARKS_TOOLS_LIST,
    )
    if result.rc != 0:
        raise FileNotFoundError(
            f"benchmark_tools.list is not readable at {HPC_BENCHMARKS_TOOLS_LIST}"
        )
    tools: list[str] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # ``pull_benchmarks.sh.j2`` runs ``$(echo "$tool" | xargs)`` — collapse
        # any embedded whitespace so we match the same effective token.
        token = " ".join(line.split())
        if token:
            tools.append(token)
    return tools


def expected_tools_for_arch(tools: list[str], arch: str) -> list[str]:
    """Return the tools staged on one architecture, per pull_benchmarks.sh.j2.

    The deployed script skips ``msr-safe`` when ``ARCH != x86_64``. Every
    other listed tool is attempted on both architectures.
    """
    if arch == "x86_64":
        return list(tools)
    return [tool for tool in tools if tool != HPC_BENCHMARKS_MSR_SAFE_PACKAGE]


def read_directory_stat(host, row, path: str) -> dict[str, str]:
    """Return a parsed stat record for one path or a 'missing' marker."""
    result = remote_command(
        host, row, PXEBOOT_COMMANDS["hpc_tools_stat"] % path
    )
    text = result.stdout.strip()
    if result.rc != 0 or text == "missing" or "|" not in text:
        return {"present": False, "mode": "", "owner": "", "group": ""}
    file_type, mode, owner, group = (text.split("|") + ["", "", "", ""])[:4]
    return {
        "present": file_type.lower() == "directory",
        "mode": mode,
        "owner": owner,
        "group": group,
    }


def list_directory(host, row, path: str) -> list[dict[str, str]]:
    """Return the immediate children of one directory as parsed records."""
    result = remote_command(
        host, row, PXEBOOT_COMMANDS["hpc_tools_list"] % path
    )
    if result.rc != 0:
        return []
    entries: list[dict[str, str]] = []
    for line in result.stdout.splitlines():
        parts = line.strip().split("|")
        if len(parts) < 3:
            continue
        entries.append({"path": parts[0], "type": parts[1], "mode": parts[2]})
    return entries


def list_tool_files(host, row, base: str) -> list[dict[str, Any]]:
    """Return every file two levels under one tool base."""
    result = remote_command(
        host, row, PXEBOOT_COMMANDS["hpc_tools_tool_files"] % base
    )
    files: list[dict[str, Any]] = []
    if result.rc != 0:
        return files
    for line in result.stdout.splitlines():
        parts = line.strip().split("|")
        if len(parts) < 3:
            continue
        try:
            size = int(parts[2])
        except ValueError:
            continue
        files.append({"path": parts[0], "type": parts[1], "size": size})
    return files


def snapshot_directories(host, row, base: str = HPC_TOOLS_BASE) -> tuple[str, ...]:
    """Return a sorted tuple of immediate subdirectories under a base path."""
    result = remote_command(
        host, row, PXEBOOT_COMMANDS["hpc_benchmarks_snapshot_dirs"] % base
    )
    if result.rc != 0:
        return ()
    return tuple(sorted(line.strip() for line in result.stdout.splitlines() if line.strip()))


def staged_tool_directories(host, row) -> list[str]:
    """Return the subset of ``/hpc_tools`` subdirs that look like tool stages.

    Only immediate children **not** in the core layout are considered — the
    core subdirs (cuda, nvidia_sdk, container_images, scripts) are created
    unconditionally by ``hpc_tools.yml``, so their presence does not indicate
    that ``pull_benchmarks.sh`` has run.
    """
    all_dirs = snapshot_directories(host, row)
    core = {f"{HPC_TOOLS_BASE.rstrip('/')}/{name}" for name in HPC_TOOLS_CORE_SUBDIRS}
    return [path for path in all_dirs if path not in core]


def source_only_scan_paths(host, row) -> list[str]:
    """Return the tool subdirectories eligible for the source-only scan.

    We intentionally skip the framework-owned directories (cuda, nvidia_sdk,
    container_images, scripts) so legitimate CUDA / NVHPC / container-runtime
    binaries do not register as "pre-compiled benchmark artifacts".
    """
    return staged_tool_directories(host, row)


def scan_for_binaries(host, row, paths: list[str]) -> list[str]:
    """Return executable files found under a bounded set of paths."""
    binaries: list[str] = []
    for path in paths:
        result = remote_command(
            host, row, PXEBOOT_COMMANDS["hpc_tools_tool_executables"] % path
        )
        if result.rc != 0:
            continue
        binaries.extend(
            line.strip() for line in result.stdout.splitlines() if line.strip()
        )
    return binaries


def pull_script_exists(host, row) -> tuple[bool, int]:
    """Return (executable, marker_count) for the deployed pull script."""
    result = remote_command(
        host,
        row,
        PXEBOOT_COMMANDS["hpc_benchmarks_pull_script_check"]
        % (HPC_BENCHMARKS_PULL_SCRIPT, HPC_BENCHMARKS_PULL_SCRIPT),
    )
    stdout = result.stdout.strip()
    try:
        markers = int(stdout.splitlines()[-1]) if stdout else 0
    except ValueError:
        markers = 0
    return result.rc == 0, markers


def tools_list_deployed(host, row) -> bool:
    """Return True when benchmark_tools.list is present at the deployed path."""
    record = read_directory_stat(host, row, HPC_BENCHMARKS_TOOLS_LIST)
    # ``read_directory_stat`` returns present=False for regular files; test
    # readability instead so file-mode + missing are distinguished cleanly.
    result = remote_command(
        host,
        row,
        PXEBOOT_COMMANDS["hpc_tools_readable"] % HPC_BENCHMARKS_TOOLS_LIST,
    )
    return result.rc == 0 or record["present"]


def pull_script_forbids_build(host, row) -> bool:
    """Return True when the deployed pull script contains no compile commands."""
    result = remote_command(
        host,
        row,
        PXEBOOT_COMMANDS["hpc_benchmarks_pull_script_no_build"]
        % HPC_BENCHMARKS_PULL_SCRIPT,
    )
    return result.rc == 0


def read_pull_script_var(host, row, variable_name: str) -> str:
    """Return the raw value of a shell assignment in the deployed script.

    Extracts ``VAR=value`` lines from ``pull_benchmarks.sh``; strips one pair
    of surrounding double quotes if present. Empty string if not found.
    """
    if not re.fullmatch(r"[A-Z_][A-Z0-9_]*", variable_name):
        raise ValueError(f"Unsafe variable name: {variable_name!r}")
    result = remote_command(
        host,
        row,
        PXEBOOT_COMMANDS["hpc_benchmarks_pull_script_var"]
        % (variable_name, variable_name, HPC_BENCHMARKS_PULL_SCRIPT),
    )
    if result.rc != 0:
        return ""
    return result.stdout.strip()


def pulp_tarball_directory(pulp_server: str, os_version: str, arch: str, tool: str) -> str:
    """Return the deployed script's canonical Pulp tarball URL for one tool."""
    return (
        f"https://{pulp_server}/pulp/content/offline_repo/cluster/"
        f"{arch}/rhel/{os_version}/tarball/{tool}/"
    )


def pulp_directory_has_files(host, row, url: str) -> tuple[bool, int]:
    """Return (has_files, count) for a Pulp directory listing seen by compute."""
    result = remote_command(
        host, row, PXEBOOT_COMMANDS["hpc_benchmarks_pulp_list"] % shlex.quote(url)
    )
    if result.rc != 0:
        return False, 0
    entries = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip() and 'href="' in line
    ]
    return bool(entries), len(entries)


def run_pull_script(host, row, timeout_seconds: int):
    """Run the deployed pull script and return the raw command result."""
    return remote_command(
        host,
        row,
        PXEBOOT_COMMANDS["hpc_benchmarks_run_pull_script"]
        % (timeout_seconds, HPC_BENCHMARKS_PULL_SCRIPT, HPC_TOOLS_BASE),
    )


def egress_probe(host, row) -> tuple[bool, str]:
    """Return (egress_open, raw_result) for the external egress probe."""
    result = remote_command(host, row, PXEBOOT_COMMANDS["hpc_benchmarks_egress_probe"])
    text = result.stdout.strip() or "failed"
    reachable = result.rc == 0 and text.isdigit() and text.startswith("2")
    return reachable, text


def rhel_version(host, row) -> str:
    """Return the VERSION_ID value from /etc/os-release on one node."""
    result = remote_command(host, row, PXEBOOT_COMMANDS["os_release"])
    if result.rc != 0:
        raise RuntimeError(command_error(result))
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("VERSION_ID="):
            return line.split("=", 1)[1].strip().strip('"')
    raise ValueError("/etc/os-release did not report VERSION_ID")


_SUMMARY_RE = re.compile(
    r"^\[INFO\]\s+(Total tools processed|Successful|Skipped|Failed):\s*(\d+)",
    re.MULTILINE,
)


def parse_staging_report(text: str) -> dict[str, int]:
    """Return per-outcome counters extracted from the pull-script output.

    Prefers the deployed script's trailing summary lines
    (``[INFO] Successful: N`` / ``Skipped: N`` / ``Failed: N``). Falls back
    to counting per-tool markers when the summary is truncated. The deployed
    script emits ``[SUCCESS]``, ``[WARN]`` (used for both "already present"
    skips and the msr-safe arch skip), and ``[ERROR]`` — it never emits
    ``[SKIP]`` or ``[FAIL]``, so we count the correct tokens here.
    """
    counters = {"total": 0, "success": 0, "skipped": 0, "failed": 0, "warn": 0}
    for match in _SUMMARY_RE.finditer(text):
        label, value = match.group(1), int(match.group(2))
        if label == "Total tools processed":
            counters["total"] = value
        elif label == "Successful":
            counters["success"] = value
        elif label == "Skipped":
            counters["skipped"] = value
        elif label == "Failed":
            counters["failed"] = value
    counters["warn"] = sum(
        1 for line in text.splitlines() if "[WARN]" in line
    )
    # If the summary was cut off, fall back to per-line marker counts so the
    # test does not miscount as zero.
    if counters["total"] == 0:
        counters["success"] = sum(
            1 for line in text.splitlines() if "[SUCCESS]" in line
        )
        counters["failed"] = sum(
            1 for line in text.splitlines() if "[ERROR]" in line
        )
        # Deployed script prints "[WARN] $tool already present ... Skipping"
        # for idempotent skips and "[WARN] $tool is x86_64 only. Skipping."
        # for arch skips. Both are counted as skipped.
        counters["skipped"] = sum(
            1
            for line in text.splitlines()
            if "[WARN]" in line and "Skipping" in line
        )
    return counters


def core_directory_records(host, row) -> list[tuple[str, dict[str, str]]]:
    """Return per-required-subdir stat records under /hpc_tools."""
    records: list[tuple[str, dict[str, str]]] = []
    for subdir in HPC_TOOLS_CORE_SUBDIRS:
        path = f"{HPC_TOOLS_BASE}/{subdir}"
        records.append((subdir, read_directory_stat(host, row, path)))
    return records


def enforce_mode_755(record: dict[str, str]) -> bool:
    """Return True when a stat record is a directory with 0755 (or 755) mode."""
    return record.get("present", False) and record.get("mode", "").lstrip("0") in {
        HPC_TOOLS_DIRECTORY_MODE.lstrip("0"),
        HPC_TOOLS_DIRECTORY_MODE,
    }


# Re-export locations of the core /hpc_tools subdirectories used by
# invariance tests (TC-14, TC-15, TC-16).
__all__ = [
    "command_error",
    "compute_architectures",
    "computes_or_skip",
    "core_directory_records",
    "detect_architecture",
    "egress_probe",
    "enforce_mode_755",
    "expected_tools_for_arch",
    "hpc_benchmarks_context",
    "list_directory",
    "list_tool_files",
    "parse_staging_report",
    "pull_script_exists",
    "pull_script_forbids_build",
    "pulp_directory_has_files",
    "pulp_tarball_directory",
    "read_benchmark_tools_list",
    "read_directory_stat",
    "read_pull_script_var",
    "rhel_version",
    "run_pull_script",
    "scan_for_binaries",
    "snapshot_directories",
    "source_only_scan_paths",
    "staged_tool_directories",
    "tools_list_deployed",
    "HPC_TOOLS_CONTAINER_IMAGES_DIRECTORY",
    "HPC_TOOLS_CUDA_DIRECTORY",
    "HPC_TOOLS_NVIDIA_SDK_DIRECTORY",
    "HPC_TOOLS_SCRIPTS_DIRECTORY",
]
