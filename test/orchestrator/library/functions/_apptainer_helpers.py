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

"""Private Apptainer context, input-validation, and execution helpers."""

import os
import re
import shlex
import time
from collections.abc import Mapping
from typing import Any

from ..vars.pxeboot_vars import (
    APPTAINER_IMAGE_DIRECTORY,
    APPTAINER_JOB_TIMEOUT_SECONDS,
    PXEBOOT_COMMANDS,
    SLURM_ACCOUNTING_POLL_SECONDS,
    SLURM_ACCOUNTING_TIMEOUT_SECONDS,
)
from ._pxeboot_helpers import remote_command
from ._workload_helpers import slurm_compute_rows, slurm_context

_SAFE_IMAGE = re.compile(
    rf"{re.escape(APPTAINER_IMAGE_DIRECTORY)}/[A-Za-z0-9_.+-]+\.sif"
)
_SAFE_NODE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,254}")
_SAFE_USERNAME = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]{0,63}")


def apptainer_context(host):
    """Return workload context, Slurm rows, controller, and compute rows."""
    context, rows, control, config = slurm_context(host)
    return context, rows, control, slurm_compute_rows(rows), config


def safe_node_name(value: str) -> str:
    """Return one shell-safe mapped Slurm node name."""
    name = str(value or "").strip()
    if not _SAFE_NODE.fullmatch(name):
        raise ValueError("Mapped Slurm node name is invalid")
    return name


def safe_username(value: str) -> str:
    """Return one shell-safe POSIX account name."""
    username = str(value or "").strip()
    if not _SAFE_USERNAME.fullmatch(username):
        raise ValueError("Test account name is invalid")
    return username


def image_inventory(host, row) -> list[dict[str, Any]]:
    """Return validated SIF metadata from one mapped node."""
    result = remote_command(host, row, PXEBOOT_COMMANDS["apptainer_find_sif"])
    if result.rc != 0:
        raise RuntimeError(command_error(result))
    images = []
    for line in result.stdout.splitlines():
        parts = line.strip().split("|", 3)
        if len(parts) != 4 or not _SAFE_IMAGE.fullmatch(parts[0]):
            continue
        try:
            size = int(parts[2])
            modified = float(parts[3])
        except ValueError as exc:
            raise ValueError("SIF inventory contains invalid metadata") from exc
        images.append(
            {
                "path": parts[0],
                "name": os.path.basename(parts[0]),
                "mode": parts[1],
                "size": size,
                "modified": modified,
            }
        )
    return images


def primary_image(host, row) -> dict[str, Any]:
    """Return the first deterministic, non-empty SIF image."""
    images = [image for image in image_inventory(host, row) if image["size"] > 0]
    if not images:
        raise FileNotFoundError(
            f"No usable SIF image exists in {APPTAINER_IMAGE_DIRECTORY}"
        )
    return images[0]


def quoted_image(path: str) -> str:
    """Validate and quote an existing SIF path for a fixed command template."""
    if not _SAFE_IMAGE.fullmatch(str(path)):
        raise ValueError("SIF image path is outside the supported directory")
    return shlex.quote(path)


def command_error(result) -> str:
    """Return a bounded command failure suitable for reports."""
    detail = (result.stderr or result.stdout or f"command rc={result.rc}").strip()
    return re.sub(r"\s+", " ", detail)[:300]


def _wait_for_job_accounting(host, control, job_id):
    """Wait for Slurm accounting to publish the job's terminal state."""
    _TERMINAL_STATES = {
        "CANCELLED",
        "COMPLETED",
        "FAILED",
        "NODE_FAIL",
        "OUT_OF_MEMORY",
        "TIMEOUT",
    }
    deadline = time.monotonic() + SLURM_ACCOUNTING_TIMEOUT_SECONDS
    state = "unavailable"
    allocated_node = "missing"
    while time.monotonic() < deadline:
        result = remote_command(
            host,
            control,
            PXEBOOT_COMMANDS["slurm_job_details"] % job_id,
        )
        output = result.stdout.strip()
        if result.rc == 0 and output:
            parts = output.split("|", 2)
            state = parts[0].strip() or "unavailable"
            allocated_node = (
                parts[1].strip() if len(parts) > 1 and parts[1].strip() else "missing"
            )
            if state.split("+", 1)[0].upper() in _TERMINAL_STATES:
                break
        time.sleep(SLURM_ACCOUNTING_POLL_SECONDS)
    normalized = state.split("+", 1)[0].upper()
    return {
        "state": state,
        "state_ok": normalized == "COMPLETED",
        "allocated_node": allocated_node,
    }


def _wait_for_array_accounting(host, control, job_id, expected_tasks):
    """Wait for Slurm accounting to publish terminal state for all array tasks.

    Unlike _wait_for_job_accounting which checks a single record via head -1,
    this queries all array task records, validates the exact expected set of
    task IDs (``<job_id>_0`` through ``<job_id>_<n-1>``), and requires every
    task to reach COMPLETED.
    """
    _TERMINAL_STATES = {
        "CANCELLED",
        "COMPLETED",
        "FAILED",
        "NODE_FAIL",
        "OUT_OF_MEMORY",
        "TIMEOUT",
    }
    expected_ids = {f"{job_id}_{i}" for i in range(expected_tasks)}
    deadline = time.monotonic() + SLURM_ACCOUNTING_TIMEOUT_SECONDS
    task_states = {}
    timed_out = True
    while time.monotonic() < deadline:
        result = remote_command(
            host,
            control,
            PXEBOOT_COMMANDS["slurm_array_job_details"] % job_id,
        )
        if result.rc == 0 and result.stdout.strip():
            task_states = {}
            for line in result.stdout.strip().splitlines():
                parts = line.strip().split("|", 2)
                if len(parts) >= 2:
                    raw_id = parts[0].strip()
                    state = parts[1].strip().split("+", 1)[0].upper()
                    # Skip the parent array record (e.g. "123_") and
                    # step records (e.g. "123_0.0")
                    if "_" in raw_id and "." not in raw_id:
                        task_states[raw_id] = state
            all_terminal = task_states and all(
                s in _TERMINAL_STATES for s in task_states.values()
            )
            if all_terminal and set(task_states.keys()) == expected_ids:
                timed_out = False
                break
        time.sleep(SLURM_ACCOUNTING_POLL_SECONDS)

    exact_match = set(task_states.keys()) == expected_ids
    all_completed = exact_match and all(
        s == "COMPLETED" for s in task_states.values()
    )
    completed_count = sum(1 for s in task_states.values() if s == "COMPLETED")
    failed_tasks = {
        tid: s for tid, s in task_states.items() if s != "COMPLETED"
    }
    error = ""
    if timed_out:
        error = (
            f"Accounting timed out after {SLURM_ACCOUNTING_TIMEOUT_SECONDS}s; "
            f"found {len(task_states)}/{expected_tasks} tasks"
        )
    elif not exact_match:
        missing = expected_ids - set(task_states.keys())
        extra = set(task_states.keys()) - expected_ids
        parts = []
        if missing:
            parts.append(f"missing={sorted(missing)}")
        if extra:
            parts.append(f"extra={sorted(extra)}")
        error = f"Task ID mismatch: {'; '.join(parts)}"
    elif failed_tasks:
        error = (
            f"{len(failed_tasks)} task(s) not COMPLETED: "
            + ", ".join(f"{tid}={s}" for tid, s in sorted(failed_tasks.items()))
        )
    return {
        "task_count": len(task_states),
        "states": task_states,
        "all_completed": all_completed,
        "summary": f"{completed_count}/{expected_tasks} COMPLETED",
        "error": error,
    }


def run_targeted_container(host, control, compute, image_path: str, username=""):
    """Run one synchronous Apptainer job on an exact mapped compute node."""
    node = safe_node_name(compute["HOSTNAME"])
    image = quoted_image(image_path)
    if username:
        command = PXEBOOT_COMMANDS["apptainer_srun_non_root"] % (
            APPTAINER_JOB_TIMEOUT_SECONDS,
            safe_username(username),
            node,
            image,
        )
    else:
        command = PXEBOOT_COMMANDS["apptainer_srun"] % (
            APPTAINER_JOB_TIMEOUT_SECONDS,
            node,
            image,
        )
    result = remote_command(host, control, command)
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    job_line = next((line for line in lines if line.startswith("OMNIA_JOB_ID=")), "")
    job_id = job_line.partition("=")[2]
    output = [line for line in lines if line != job_line]
    hostname = output[-1].split(".", 1)[0] if output else ""
    output_ok = result.rc == 0 and hostname == compute["HOSTNAME"]

    # Verify scheduler completion state via sacct
    accounting = (
        _wait_for_job_accounting(host, control, job_id)
        if job_id
        else {"state": "unavailable", "state_ok": False, "allocated_node": "missing"}
    )
    allocated_ok = accounting["allocated_node"].split(".", 1)[0] == compute["HOSTNAME"]
    success = output_ok and accounting["state_ok"] and allocated_ok
    return {
        "success": success,
        "job_id": job_id or "not reported",
        "output": "\n".join(output) or "none",
        "scheduler_state": accounting["state"],
        "scheduler_ok": accounting["state_ok"],
        "allocated_node": accounting["allocated_node"],
        "error": "" if success else command_error(result),
    }


def grouped_node_fields(rows, outcomes: Mapping[str, tuple[bool, str]]):
    """Render Apptainer outcomes using the standard functional-group layout."""
    fields = []
    groups: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        groups.setdefault(row["EXPECTED_FUNCTIONAL_GROUP"], []).append(row)
    for group_name, group_rows in sorted(groups.items()):
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
