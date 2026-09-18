#!/usr/bin/python
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

"""Orchestrate parallel image builds with configurable concurrency control.

Replaces the Ansible async+poll pattern with a Python ThreadPoolExecutor
that provides:
  - Configurable max_parallel (0 = unlimited)
  - Per-build status tracking (queued → running → completed/failed)
  - Structured results with duration and log paths
  - Graceful error handling with partial success support
"""

from __future__ import annotations

import os
import shlex
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r"""
---
module: image_build_orchestrator
short_description: Orchestrate parallel OS image builds with concurrency control
description:
  - Runs podman image builds in parallel using a thread pool.
  - Supports configurable max_parallel to limit concurrent builds.
  - Returns per-build results with status, duration, and log paths.
options:
  build_commands:
    description: >
      List of build command dicts. Each dict must contain:
        - name: functional group name (e.g., slurm_node_x86_64)
        - cmd: full podman run command string
        - log_path: path to the build log file
    type: list
    elements: dict
    required: true
  max_parallel:
    description: >
      Maximum number of concurrent builds.
      0 means unlimited (all builds run simultaneously).
    type: int
    default: 0
  timeout:
    description: Per-build timeout in seconds.
    type: int
    default: 7200
author:
  - Dell Omnia Team
"""

EXAMPLES = r"""
- name: Build images in parallel (max 4 concurrent)
  omnia.image_build.image_build_orchestrator:
    build_commands:
      - name: slurm_node_x86_64
        cmd: "podman run --rm image-builder build slurm_node"
        log_path: /opt/omnia/image_build_manager/log/slurm_node_x86_64.log
      - name: os_x86_64
        cmd: "podman run --rm image-builder build os"
        log_path: /opt/omnia/image_build_manager/log/os_x86_64.log
    max_parallel: 4
    timeout: 7200
  register: build_results

- name: Display build summary
  ansible.builtin.debug:
    var: build_results.summary
"""

RETURN = r"""
results:
  description: Per-build result list.
  type: list
  elements: dict
  contains:
    name:
      description: Functional group name.
      type: str
    status:
      description: Build status (completed, failed, timeout).
      type: str
    duration_seconds:
      description: Wall-clock time for this build.
      type: float
    log_path:
      description: Path to the build log.
      type: str
    return_code:
      description: Process exit code (-1 if timeout or error).
      type: int
    error:
      description: Error message if failed (includes last 20 lines of log).
      type: str
    log_tail:
      description: Last 20 lines of the build log (populated on failure).
      type: str
summary:
  description: Summary counts.
  type: dict
  contains:
    total:
      type: int
    completed:
      type: int
    failed:
      type: int
"""


LOG_TAIL_LINES = 20


def _read_log_tail(log_path: str, lines: int = LOG_TAIL_LINES) -> str:
    """Read last N lines from a log file for error diagnostics."""
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
            tail = all_lines[-lines:] if len(all_lines) > lines else all_lines
            return "".join(tail).strip()
    except OSError:
        return "(log file not readable)"


def _run_build(
    name: str,
    cmd: str,
    log_path: str,
    timeout: int,
) -> dict[str, Any]:
    """Execute a single image build and return structured result."""
    start_time = time.monotonic()
    result: dict[str, Any] = {
        "name": name,
        "log_path": log_path,
        "return_code": -1,
        "error": "",
        "log_tail": "",
    }

    try:
        # Ensure log directory exists
        log_dir = os.path.dirname(log_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        # Tokenize the command with shlex (POSIX shell quoting rules) and
        # execute the resulting argument vector directly — no shell is
        # invoked. This avoids passing a raw string to "bash -c", which
        # would let any shell metacharacter in a templated value (image
        # names, mount paths, credentials) be interpreted by the shell
        # instead of treated as literal argument text (command/argument
        # injection).
        argv = shlex.split(cmd)
        with open(log_path, "w", encoding="utf-8") as log_file:
            proc = subprocess.run(
                argv,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                check=False,
                shell=False,
            )
            result["return_code"] = proc.returncode
            if proc.returncode == 0:
                result["status"] = "completed"
            else:
                result["status"] = "failed"
                log_tail = _read_log_tail(log_path)
                result["log_tail"] = log_tail
                result["error"] = (
                    f"Build '{name}' exited with code {proc.returncode}. "
                    f"Log: {log_path}\n"
                    f"--- Last {LOG_TAIL_LINES} lines ---\n{log_tail}"
                )

    except subprocess.TimeoutExpired:
        result["status"] = "timeout"
        log_tail = _read_log_tail(log_path)
        result["log_tail"] = log_tail
        result["error"] = (
            f"Build '{name}' timed out after {timeout}s. "
            f"Log: {log_path}\n"
            f"--- Last {LOG_TAIL_LINES} lines ---\n{log_tail}"
        )
    except ValueError as exc:
        # Raised by shlex.split() on malformed quoting in cmd.
        result["status"] = "failed"
        result["error"] = f"Failed to parse build command for '{name}': {exc}"
    except OSError as exc:
        result["status"] = "failed"
        result["error"] = f"Failed to execute build '{name}': {exc}"

    result["duration_seconds"] = round(time.monotonic() - start_time, 2)
    return result


def main() -> None:
    """Module entry point."""
    module = AnsibleModule(
        argument_spec=dict(
            build_commands=dict(
                type="list", elements="dict", required=True,
                options=dict(
                    name=dict(type="str", required=True),
                    cmd=dict(type="str", required=True),
                    log_path=dict(type="str", required=True),
                ),
            ),
            max_parallel=dict(type="int", default=0),
            timeout=dict(type="int", default=7200),
        ),
        supports_check_mode=True,
    )

    build_commands: list[dict[str, str]] = module.params["build_commands"]
    max_parallel: int = module.params["max_parallel"]
    timeout: int = module.params["timeout"]

    if not build_commands:
        module.exit_json(
            changed=False,
            results=[],
            summary={"total": 0, "completed": 0, "failed": 0},
            msg="No builds to execute",
        )

    if module.check_mode:
        module.exit_json(
            changed=False,
            results=[{"name": b["name"], "status": "skipped"} for b in build_commands],
            summary={"total": len(build_commands), "completed": 0, "failed": 0},
            msg="Check mode — no builds executed",
        )

    # Determine worker count
    workers = len(build_commands) if max_parallel <= 0 else min(max_parallel, len(build_commands))

    results: list[dict[str, Any]] = []
    futures_map: dict[Any, str] = {}

    with ThreadPoolExecutor(max_workers=workers) as executor:
        for build in build_commands:
            future = executor.submit(
                _run_build,
                name=build["name"],
                cmd=build["cmd"],
                log_path=build["log_path"],
                timeout=timeout,
            )
            futures_map[future] = build["name"]

        for future in as_completed(futures_map):
            try:
                result = future.result()
            except Exception as exc:
                result = {
                    "name": futures_map[future],
                    "status": "failed",
                    "duration_seconds": 0,
                    "log_path": "",
                    "return_code": -1,
                    "error": str(exc),
                }
            results.append(result)

    # Sort results to match input order
    name_order = {b["name"]: i for i, b in enumerate(build_commands)}
    results.sort(key=lambda r: name_order.get(r["name"], 999))

    completed_count = sum(1 for r in results if r["status"] == "completed")
    failed_count = len(results) - completed_count
    summary = {
        "total": len(results),
        "completed": completed_count,
        "failed": failed_count,
    }

    if failed_count > 0:
        failed_details = []
        for r in results:
            if r["status"] != "completed":
                detail = (
                    f"  - {r['name']}: {r['status']} "
                    f"(rc={r.get('return_code', -1)}, "
                    f"{r.get('duration_seconds', 0):.1f}s) "
                    f"→ {r.get('log_path', 'N/A')}"
                )
                failed_details.append(detail)
        detail_str = "\n".join(failed_details)
        module.fail_json(
            msg=(
                f"{failed_count}/{len(results)} builds failed:\n"
                f"{detail_str}\n"
                f"Check the log files above for full error details."
            ),
            changed=True,
            results=results,
            summary=summary,
        )
    else:
        completed_details = []
        for r in results:
            completed_details.append(
                f"  - {r['name']}: {r.get('duration_seconds', 0):.1f}s"
            )
        module.exit_json(
            changed=True,
            results=results,
            summary=summary,
            msg=(
                f"All {completed_count} builds completed successfully:\n"
                + "\n".join(completed_details)
            ),
        )


if __name__ == "__main__":
    main()
