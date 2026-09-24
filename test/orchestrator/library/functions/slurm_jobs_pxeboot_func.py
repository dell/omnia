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

"""Slurm functional job and scheduler-state verification after PXE."""

import base64
import re
import secrets
import shlex
import time
from pathlib import Path

from ..vars.pxeboot_vars import (
    PXEBOOT_COMMANDS,
    RECOVERY_POLL_SECONDS,
    SLURM_ACCOUNTING_POLL_SECONDS,
    SLURM_ACCOUNTING_TIMEOUT_SECONDS,
    SLURM_COMPILER_PREFIX,
    SLURM_CONCURRENT_JOB_COMMAND,
    SLURM_CONTROL_PREFIX,
    SLURM_DRAIN_REASON,
    SLURM_JOB_TIMEOUT_SECONDS,
    SLURM_LOGIN_PREFIX,
    SLURM_TEST_JOB_COMMAND,
)
from ._pxeboot_helpers import (
    first_row,
    marker_is_authorized,
    remote_command,
    runtime_exception,
    runtime_result,
)
from ._workload_helpers import optional_skip as _skip
from ._workload_helpers import require_functional as _require_functional
from ._workload_helpers import slurm_compute_rows as _compute_rows
from ._workload_helpers import slurm_context as _context
from ._workload_helpers import slurm_gpu_rows as _gpu_rows
from ._workload_helpers import slurm_shared_storage as _shared_storage

_OPENMPI_RECORD_RE = re.compile(r"^(OPENMPI_EXECUTABLE|OPENMPI_COMPILER)\|(.+)$")
_MPI_RESULT_RE = re.compile(r"^(\d+)/(\d+)\|([A-Za-z0-9_.-]+)$")


def _wait_for_targeted_job_accounting(host, control, job_id):
    """Wait for Slurm accounting to publish a targeted job's final record."""
    deadline = time.monotonic() + SLURM_ACCOUNTING_TIMEOUT_SECONDS
    state = "unavailable"
    allocated_node = "missing"
    accounting_error = ""
    terminal_states = {
        "CANCELLED",
        "COMPLETED",
        "FAILED",
        "NODE_FAIL",
        "OUT_OF_MEMORY",
        "TIMEOUT",
    }
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
            if state.split("+", 1)[0].upper() in terminal_states:
                break
        elif result.rc != 0:
            accounting_error = re.sub(
                r"\s+", " ", (result.stderr or result.stdout).strip()
            )[:500]
        time.sleep(SLURM_ACCOUNTING_POLL_SECONDS)
    normalized_state = state.split("+", 1)[0].upper()
    return {
        "state": state,
        "state_ok": normalized_state == "COMPLETED",
        "allocated_node": allocated_node,
        "accounting_error": accounting_error,
    }


def _mapped_compute_readiness(host, control, compute_rows):
    """Return normalized scheduler readiness for every mapped compute."""
    scheduler = remote_command(
        host,
        control,
        PXEBOOT_COMMANDS["slurm_partitions"],
    )
    if scheduler.rc != 0:
        raise RuntimeError("sinfo could not read mapped compute-node state")
    node_states = {}
    for line in scheduler.stdout.splitlines():
        parts = [part.strip() for part in line.split("|", 3)]
        if len(parts) != 4 or not parts[0]:
            continue
        node = parts[0].split(".", 1)[0]
        state = parts[2].lower().split("+", 1)[0].rstrip("*~#$@!%^")
        availability = parts[3].lower()
        node_states.setdefault(node, []).append((state, availability))
    readiness = []
    for row in compute_rows:
        states = node_states.get(row["HOSTNAME"], [])
        idle = bool(states) and all(
            state == "idle" and availability == "up" for state, availability in states
        )
        readiness.append(
            {
                "row": row,
                "idle": idle,
                "state": ", ".join(sorted({state for state, _availability in states}))
                or "missing",
                "availability": ", ".join(
                    sorted({availability for _state, availability in states})
                )
                or "missing",
            }
        )
    return readiness


def _run_targeted_srun(host, control, submission_row, compute_row):
    """Run and attest one uniquely identified Slurm job on one compute node."""
    result = remote_command(
        host,
        submission_row,
        PXEBOOT_COMMANDS["slurm_srun_node"] % compute_row["HOSTNAME"],
    )
    output_lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    job_marker = next(
        (line for line in output_lines if line.startswith("OMNIA_JOB_ID=")),
        "",
    )
    job_id = job_marker.partition("=")[2].strip()
    job_id_ok = bool(re.fullmatch(r"[0-9]+", job_id))
    job_output_lines = [line for line in output_lines if line != job_marker]
    job_output = "\n".join(job_output_lines)
    output_hostname = job_output_lines[-1].split(".", 1)[0] if job_output_lines else ""
    output_ok = output_hostname == compute_row["HOSTNAME"]
    accounting = (
        _wait_for_targeted_job_accounting(host, control, job_id)
        if job_id_ok
        else {
            "state": "unavailable",
            "state_ok": False,
            "allocated_node": "missing",
            "accounting_error": "Slurm job ID was not reported",
        }
    )
    allocated_hostname = accounting["allocated_node"].split(".", 1)[0]
    allocated_ok = allocated_hostname == compute_row["HOSTNAME"]
    stderr = re.sub(r"\s+", " ", result.stderr.strip())[:500]
    errors = [value for value in (stderr, accounting["accounting_error"]) if value]
    return {
        "success": (
            result.rc == 0
            and job_id_ok
            and output_ok
            and accounting["state_ok"]
            and allocated_ok
        ),
        "job_command": SLURM_TEST_JOB_COMMAND,
        "job_id": job_id or "missing",
        "job_id_ok": job_id_ok,
        "state": accounting["state"],
        "state_ok": accounting["state_ok"],
        "allocated_node": accounting["allocated_node"],
        "allocated_ok": allocated_ok,
        "job_output": job_output or "none",
        "output_ok": output_ok,
        "error_output": " | ".join(errors),
    }


def _check_slurm_role_jobs(host, role_prefix, summary, missing_role):
    """Run a targeted job on every compute from every node of one role."""
    try:
        gated = _require_functional(summary)
        if gated:
            return gated
        _runtime, rows, control, _config = _context(host)
        compute_rows = _compute_rows(rows)
        if not compute_rows:
            return _skip(summary, "No Slurm compute nodes are mapped")
        submission_rows = [
            row
            for row in rows
            if row["EXPECTED_FUNCTIONAL_GROUP"].startswith(role_prefix)
        ]
        if not submission_rows:
            return _skip(summary, f"No {missing_role} nodes are mapped")
        fields = []
        failed = []
        for submission_row in submission_rows:
            target_results = [
                (
                    compute_row,
                    _run_targeted_srun(
                        host,
                        control,
                        submission_row,
                        compute_row,
                    ),
                )
                for compute_row in compute_rows
            ]
            passed = sum(1 for _row, result in target_results if result["success"])
            fields.extend(
                [
                    (
                        "Submission node",
                        (
                            f"{submission_row['HOSTNAME']} | "
                            f"{submission_row['ADMIN_IP']}"
                        ),
                    ),
                    ("Targeted compute jobs", f"{passed}/{len(target_results)}"),
                ]
            )
            grouped_results = {}
            for compute_row, result in target_results:
                grouped_results.setdefault(
                    compute_row["EXPECTED_FUNCTIONAL_GROUP"], []
                ).append((compute_row, result))
            for group_name, group_results in grouped_results.items():
                group_passed = sum(
                    1 for _row, result in group_results if result["success"]
                )
                fields.append(
                    (
                        "Functional group",
                        f"[{group_name}] ({group_passed}/{len(group_results)})",
                    )
                )
                for compute_row, result in group_results:
                    fields.extend(
                        [
                            (
                                f"  {compute_row['HOSTNAME']}",
                                (
                                    f"{'✓' if result['success'] else '✗'} "
                                    f"{compute_row['ADMIN_IP']}"
                                ),
                            ),
                            ("    Job command", result["job_command"]),
                            (
                                "    Job ID",
                                (
                                    f"{'✓' if result['job_id_ok'] else '✗'} "
                                    f"{result['job_id']}"
                                ),
                            ),
                            (
                                "    Job state",
                                (
                                    f"{'✓' if result['state_ok'] else '✗'} "
                                    f"{result['state']}"
                                ),
                            ),
                            (
                                "    Allocated node",
                                (
                                    f"{'✓' if result['allocated_ok'] else '✗'} "
                                    f"{result['allocated_node']}"
                                ),
                            ),
                            (
                                "    Job output",
                                (
                                    f"{'✓' if result['output_ok'] else '✗'} "
                                    f"{result['job_output']}"
                                ),
                            ),
                        ]
                    )
                    if result["error_output"]:
                        fields.append(("    Error output", result["error_output"]))
                    if not result["success"]:
                        failed.append(
                            f"{submission_row['HOSTNAME']}->{compute_row['HOSTNAME']}"
                        )
        return runtime_result(
            not failed,
            summary,
            fields,
            "Targeted jobs failed: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_slurm_control_node_jobs(host):
    """Run one targeted job per compute from every Slurm control node."""
    return _check_slurm_role_jobs(
        host,
        SLURM_CONTROL_PREFIX,
        "Slurm control-node job submission",
        "Slurm control",
    )


def check_slurm_login_node_jobs(host):
    """Run one targeted job per compute from every login node."""
    return _check_slurm_role_jobs(
        host,
        SLURM_LOGIN_PREFIX,
        "Slurm login-node job submission",
        "login",
    )


def check_slurm_compiler_node_jobs(host):
    """Run one targeted job per compute from every login compiler node."""
    return _check_slurm_role_jobs(
        host,
        SLURM_COMPILER_PREFIX,
        "Slurm login-compiler job submission",
        "login-compiler",
    )


def check_slurm_concurrent_jobs(host):
    """Run one concurrent targeted job per initially idle compute node."""
    summary = "Slurm concurrent batch jobs"
    submitted_jobs = []
    control = None
    try:
        gated = _require_functional(summary)
        if gated:
            return gated
        _runtime, rows, control, _config = _context(host)
        compute_rows = _compute_rows(rows)
        if not compute_rows:
            return _skip(summary, "No Slurm compute nodes are mapped")

        initial_queue = remote_command(
            host,
            control,
            PXEBOOT_COMMANDS["slurm_queue_snapshot"],
        )
        if initial_queue.rc != 0:
            raise RuntimeError("squeue could not read the initial scheduler queue")
        initial_jobs = [
            line.strip() for line in initial_queue.stdout.splitlines() if line.strip()
        ]
        if initial_jobs:
            return runtime_result(
                False,
                summary,
                [
                    ("Initial queue", f"✗ {len(initial_jobs)} active job(s)"),
                    *[("  Active job", job) for job in initial_jobs],
                ],
                "Concurrent-job validation requires an initially empty Slurm queue",
            )

        readiness = _mapped_compute_readiness(host, control, compute_rows)
        idle_count = sum(1 for item in readiness if item["idle"])
        if idle_count != len(compute_rows):
            fields = [
                ("Initial queue", "✓ 0 active jobs"),
                (
                    "Initially idle compute nodes",
                    f"✗ {idle_count}/{len(compute_rows)}",
                ),
            ]
            fields.extend(
                (
                    f"  {row['HOSTNAME']}",
                    f"{'✓' if idle else '✗'} {row['ADMIN_IP']} | state={state}",
                )
                for item in readiness
                for row, idle, state in [(item["row"], item["idle"], item["state"])]
            )
            return runtime_result(
                False,
                summary,
                fields,
                "Every mapped compute node must be idle before this test",
            )

        job_results = []
        for row in compute_rows:
            submission = remote_command(
                host,
                control,
                PXEBOOT_COMMANDS["slurm_submit_concurrent_job"] % row["HOSTNAME"],
            )
            job_id = submission.stdout.strip().split(";", 1)[0]
            submitted = submission.rc == 0 and bool(re.fullmatch(r"[0-9]+", job_id))
            if submitted:
                submitted_jobs.append((row, job_id))
            job_results.append(
                {
                    "row": row,
                    "submitted": submitted,
                    "job_id": job_id or "missing",
                    "submission_error": re.sub(
                        r"\s+",
                        " ",
                        (submission.stderr or submission.stdout).strip(),
                    )[:500],
                }
            )

        for job in job_results:
            row = job["row"]
            if not job["submitted"]:
                job.update(
                    {
                        "state": "not submitted",
                        "state_ok": False,
                        "allocated_node": "missing",
                        "allocated_ok": False,
                        "stdout": "none",
                        "stdout_ok": False,
                        "stderr": job["submission_error"] or "submission failed",
                        "stderr_ok": False,
                        "success": False,
                    }
                )
                continue
            job_id = job["job_id"]
            accounting = _wait_for_targeted_job_accounting(
                host,
                control,
                job_id,
            )
            stdout_result = remote_command(
                host,
                row,
                PXEBOOT_COMMANDS["slurm_concurrent_job_stdout"] % job_id,
            )
            stderr_result = remote_command(
                host,
                row,
                PXEBOOT_COMMANDS["slurm_concurrent_job_stderr"] % job_id,
            )
            stdout = stdout_result.stdout.strip() or "none"
            stderr = stderr_result.stdout.strip()
            allocated_ok = (
                accounting["allocated_node"].split(".", 1)[0] == row["HOSTNAME"]
            )
            stdout_ok = (
                stdout_result.rc == 0
                and stdout.splitlines()[-1].split(".", 1)[0] == row["HOSTNAME"]
            )
            stderr_ok = stderr_result.rc == 0 and not stderr
            success = (
                accounting["state_ok"] and allocated_ok and stdout_ok and stderr_ok
            )
            job.update(
                {
                    "state": accounting["state"],
                    "state_ok": accounting["state_ok"],
                    "allocated_node": accounting["allocated_node"],
                    "allocated_ok": allocated_ok,
                    "stdout": stdout,
                    "stdout_ok": stdout_ok,
                    "stderr": stderr or accounting["accounting_error"] or "none",
                    "stderr_ok": stderr_ok and not accounting["accounting_error"],
                    "success": success and not accounting["accounting_error"],
                }
            )

        final_queue = remote_command(
            host,
            control,
            PXEBOOT_COMMANDS["slurm_queue_snapshot"],
        )
        final_jobs = [
            line.strip() for line in final_queue.stdout.splitlines() if line.strip()
        ]
        queue_ok = final_queue.rc == 0 and not final_jobs
        fields = [
            ("Initial queue", "✓ 0 active jobs"),
            (
                "Initially idle compute nodes",
                f"✓ {idle_count}/{len(compute_rows)}",
            ),
            (
                "Jobs submitted before waiting",
                f"{len(submitted_jobs)}/{len(compute_rows)}",
            ),
        ]
        grouped = {}
        for job in job_results:
            grouped.setdefault(job["row"]["EXPECTED_FUNCTIONAL_GROUP"], []).append(job)
        for group_name, group_jobs in grouped.items():
            valid = sum(1 for job in group_jobs if job["success"])
            fields.append(
                ("Functional group", f"[{group_name}] ({valid}/{len(group_jobs)})")
            )
            for job in group_jobs:
                row = job["row"]
                fields.extend(
                    [
                        (
                            f"  {row['HOSTNAME']}",
                            f"{'✓' if job['success'] else '✗'} {row['ADMIN_IP']}",
                        ),
                        ("    Job command", SLURM_CONCURRENT_JOB_COMMAND),
                        (
                            "    Job ID",
                            f"{'✓' if job['submitted'] else '✗'} {job['job_id']}",
                        ),
                        (
                            "    Job state",
                            f"{'✓' if job['state_ok'] else '✗'} {job['state']}",
                        ),
                        (
                            "    Allocated node",
                            (
                                f"{'✓' if job['allocated_ok'] else '✗'} "
                                f"{job['allocated_node']}"
                            ),
                        ),
                        (
                            "    Standard output",
                            f"{'✓' if job['stdout_ok'] else '✗'} {job['stdout']}",
                        ),
                        (
                            "    Error output",
                            f"{'✓' if job['stderr_ok'] else '✗'} {job['stderr']}",
                        ),
                    ]
                )
        fields.append(
            (
                "Final queue",
                f"{'✓' if queue_ok else '✗'} {len(final_jobs)} active job(s)",
            )
        )
        fields.extend(("  Remaining job", job) for job in final_jobs)
        failures = [job["row"]["HOSTNAME"] for job in job_results if not job["success"]]
        success = not failures and queue_ok
        return runtime_result(
            success,
            summary,
            fields,
            (
                "Concurrent jobs failed on: " + ", ".join(failures)
                if failures
                else "Slurm queue was not empty after the submitted jobs completed"
            )
            if not success
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
    finally:
        if control is not None:
            for row, job_id in submitted_jobs:
                try:
                    remote_command(
                        host,
                        control,
                        PXEBOOT_COMMANDS["slurm_cancel_job"] % job_id,
                    )
                    remote_command(
                        host,
                        row,
                        PXEBOOT_COMMANDS["slurm_cleanup_concurrent_job"]
                        % (job_id, job_id),
                    )
                except (OSError, RuntimeError, TypeError, ValueError):
                    pass


def check_slurm_insufficient_resources(host):
    """Verify an impossible immediate allocation is rejected."""
    summary = "Slurm insufficient-resource handling"
    try:
        gated = _require_functional(summary)
        if gated:
            return gated
        _runtime, rows, control, _config = _context(host)
        if not rows or not _compute_rows(rows):
            return _skip(summary, "No Slurm compute nodes are mapped")
        result = remote_command(
            host,
            control,
            PXEBOOT_COMMANDS["slurm_insufficient_resources"],
        )
        rejected = result.rc != 0
        return runtime_result(
            rejected,
            summary,
            [("Impossible allocation", "rejected" if rejected else "accepted")],
            "Slurm accepted a request larger than the available node count"
            if not rejected
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def _wait_for_slurm_job(host, control, job_id: str, expected: str):
    deadline = time.monotonic() + SLURM_JOB_TIMEOUT_SECONDS
    state = ""
    while time.monotonic() < deadline:
        result = remote_command(
            host,
            control,
            PXEBOOT_COMMANDS["slurm_job_state"] % (job_id, job_id),
        )
        state = result.stdout.strip().partition("|")[0]
        if result.rc == 0 and state == expected:
            return True, state
        if state in {"CANCELLED", "COMPLETED", "FAILED", "TIMEOUT"}:
            return False, state
        time.sleep(RECOVERY_POLL_SECONDS)
    return False, state


def _wait_for_queued_job(host, control, job_id: str):
    """Wait for one submitted job to become pending and return its reason."""
    deadline = time.monotonic() + SLURM_JOB_TIMEOUT_SECONDS
    state = "unavailable"
    reason = "unavailable"
    while time.monotonic() < deadline:
        result = remote_command(
            host,
            control,
            PXEBOOT_COMMANDS["slurm_queue_job_state"] % job_id,
        )
        output = result.stdout.strip()
        state, separator, reason = output.partition("|")
        state = state.split("+", 1)[0].upper() or "unavailable"
        reason = reason.strip() if separator else "unavailable"
        if result.rc == 0 and state == "PENDING":
            return True, state, reason
        if state in {"RUNNING", "CANCELLED", "COMPLETED", "FAILED", "TIMEOUT"}:
            return False, state, reason
        time.sleep(RECOVERY_POLL_SECONDS)
    return False, state, reason


def _queue_job_artifacts(host, row, job_id: str):
    """Read bounded stdout and stderr for one queue-validation job."""
    stdout_result = remote_command(
        host,
        row,
        PXEBOOT_COMMANDS["slurm_queue_job_stdout"] % job_id,
    )
    stderr_result = remote_command(
        host,
        row,
        PXEBOOT_COMMANDS["slurm_queue_job_stderr"] % job_id,
    )
    stdout = stdout_result.stdout.strip() or "none"
    stderr = stderr_result.stdout.strip()
    return (
        stdout,
        stderr or "none",
        stdout_result.rc == 0,
        (stderr_result.rc == 0 and not stderr),
    )


def check_slurm_job_queueing(host):
    """Saturate all idle computes, then verify one extra job queues and runs."""
    summary = "Slurm job queueing behavior"
    jobs: list[str] = []
    computes = []
    control = None
    try:
        gated = _require_functional(summary)
        if gated:
            return gated
        _runtime, rows, control, _config = _context(host)
        computes = _compute_rows(rows)
        if not computes:
            return _skip(summary, "No Slurm compute nodes are mapped")

        initial_queue = remote_command(
            host,
            control,
            PXEBOOT_COMMANDS["slurm_queue_snapshot"],
        )
        if initial_queue.rc != 0:
            raise RuntimeError("squeue could not read the initial scheduler queue")
        initial_jobs = [
            line.strip() for line in initial_queue.stdout.splitlines() if line.strip()
        ]
        if initial_jobs:
            return runtime_result(
                False,
                summary,
                [
                    ("Initial queue", f"✗ {len(initial_jobs)} active job(s)"),
                    *[("  Active job", job) for job in initial_jobs],
                ],
                "Queue validation requires an initially empty Slurm queue",
            )

        readiness = _mapped_compute_readiness(host, control, computes)
        idle_count = sum(1 for item in readiness if item["idle"])
        if idle_count != len(computes):
            fields = [
                ("Initial queue", "✓ 0 active jobs"),
                ("Mapped compute nodes", str(len(computes))),
                ("Initially idle compute nodes", f"✗ {idle_count}/{len(computes)}"),
            ]
            for item in readiness:
                row = item["row"]
                fields.extend(
                    [
                        (
                            f"  {row['HOSTNAME']}",
                            f"{'✓' if item['idle'] else '✗'} {row['ADMIN_IP']}",
                        ),
                        ("    State", item["state"]),
                        ("    Partition availability", item["availability"]),
                    ]
                )
            return runtime_result(
                False,
                summary,
                fields,
                "Every mapped compute node must be idle before queue saturation",
            )

        holders = []
        for item in readiness:
            row = item["row"]
            command = PXEBOOT_COMMANDS["slurm_submit_queue_holder"] % row["HOSTNAME"]
            submission = remote_command(host, control, command)
            job_id = submission.stdout.strip().split(";", 1)[0]
            submitted = submission.rc == 0 and job_id.isdigit()
            if submitted:
                jobs.append(job_id)
            holders.append(
                {
                    "row": row,
                    "command": command,
                    "job_id": job_id or "missing",
                    "submitted": submitted,
                    "submission_error": re.sub(
                        r"\s+",
                        " ",
                        (submission.stderr or submission.stdout).strip(),
                    )[:500],
                }
            )

        for holder in holders:
            if holder["submitted"]:
                running, state = _wait_for_slurm_job(
                    host,
                    control,
                    holder["job_id"],
                    "RUNNING",
                )
            else:
                running, state = False, "not submitted"
            holder["running"] = running
            holder["running_state"] = state or "unknown"

        all_holders_running = bool(holders) and all(
            holder["running"] for holder in holders
        )
        follower_targets = ",".join(item["row"]["HOSTNAME"] for item in readiness)
        follower_command = (
            PXEBOOT_COMMANDS["slurm_submit_queue_follower"] % follower_targets
        )
        follower_submission = remote_command(host, control, follower_command)
        follower_id = follower_submission.stdout.strip().split(";", 1)[0]
        follower_submitted = follower_submission.rc == 0 and follower_id.isdigit()
        if follower_submitted:
            jobs.append(follower_id)
        pending, pending_state, pending_reason = (
            _wait_for_queued_job(host, control, follower_id)
            if follower_submitted and all_holders_running
            else (False, "not checked", "saturation jobs were not all running")
        )

        for holder in holders:
            if holder["submitted"]:
                completed, final_record = _wait_for_slurm_job(
                    host,
                    control,
                    holder["job_id"],
                    "COMPLETED",
                )
                accounting = _wait_for_targeted_job_accounting(
                    host,
                    control,
                    holder["job_id"],
                )
                stdout, stderr, stdout_read, stderr_ok = _queue_job_artifacts(
                    host,
                    holder["row"],
                    holder["job_id"],
                )
            else:
                completed, final_record = False, "not submitted"
                accounting = {
                    "allocated_node": "missing",
                    "accounting_error": holder["submission_error"],
                }
                stdout, stderr, stdout_read, stderr_ok = (
                    "none",
                    holder["submission_error"] or "submission failed",
                    False,
                    False,
                )
            expected_node = holder["row"]["HOSTNAME"]
            allocated_node = accounting["allocated_node"]
            allocated_ok = allocated_node.split(".", 1)[0] == expected_node
            output_ok = stdout_read and stdout.split(".", 1)[0] == expected_node
            holder.update(
                {
                    "completed": completed,
                    "final_state": final_record or "unknown",
                    "allocated_node": allocated_node,
                    "allocated_ok": allocated_ok,
                    "stdout": stdout,
                    "output_ok": output_ok,
                    "stderr": stderr,
                    "stderr_ok": stderr_ok and not accounting["accounting_error"],
                    "success": (
                        holder["submitted"]
                        and holder["running"]
                        and completed
                        and allocated_ok
                        and output_ok
                        and stderr_ok
                        and not accounting["accounting_error"]
                    ),
                }
            )

        follower_completed, follower_final_record = (
            _wait_for_slurm_job(
                host,
                control,
                follower_id,
                "COMPLETED",
            )
            if follower_submitted
            else (False, "not submitted")
        )
        follower_accounting = (
            _wait_for_targeted_job_accounting(
                host,
                control,
                follower_id,
            )
            if follower_submitted
            else {
                "allocated_node": "missing",
                "accounting_error": "follower job was not submitted",
            }
        )
        follower_allocated = follower_accounting["allocated_node"].split(".", 1)[0]
        allocated_row = next(
            (row for row in computes if row["HOSTNAME"] == follower_allocated),
            None,
        )
        if allocated_row is not None:
            (
                follower_stdout,
                follower_stderr,
                follower_stdout_read,
                follower_stderr_ok,
            ) = _queue_job_artifacts(host, allocated_row, follower_id)
        else:
            (
                follower_stdout,
                follower_stderr,
                follower_stdout_read,
                follower_stderr_ok,
            ) = (
                "none",
                follower_accounting["accounting_error"] or "allocated node is invalid",
                False,
                False,
            )
        follower_output_ok = (
            follower_stdout_read
            and follower_stdout.split(".", 1)[0] == follower_allocated
            and follower_allocated in {row["HOSTNAME"] for row in computes}
        )

        final_queue = remote_command(
            host,
            control,
            PXEBOOT_COMMANDS["slurm_queue_snapshot"],
        )
        remaining_jobs = [
            line.strip() for line in final_queue.stdout.splitlines() if line.strip()
        ]
        queue_empty = final_queue.rc == 0 and not remaining_jobs
        follower_success = (
            follower_submitted
            and pending
            and follower_completed
            and allocated_row is not None
            and follower_output_ok
            and follower_stderr_ok
            and not follower_accounting["accounting_error"]
        )
        fields = [
            ("Initial queue", "✓ 0 active jobs"),
            ("Mapped compute nodes", str(len(computes))),
            ("Initially idle compute nodes", f"✓ {idle_count}/{len(computes)}"),
            (
                "Queue test design",
                f"{len(computes)} exclusive saturation jobs + 1 follower job",
            ),
            (
                "Saturation reached",
                (
                    f"{'✓' if all_holders_running else '✗'} "
                    f"{sum(1 for holder in holders if holder['running'])}/{len(holders)} "
                    "jobs running"
                ),
            ),
        ]
        for holder in holders:
            row = holder["row"]
            fields.extend(
                [
                    (
                        f"  Saturation target {row['HOSTNAME']}",
                        f"{'✓' if holder['success'] else '✗'} {row['ADMIN_IP']}",
                    ),
                    ("    Job command", holder["command"]),
                    (
                        "    Job submitted",
                        (
                            f"{'✓' if holder['submitted'] else '✗'} "
                            f"job ID {holder['job_id']}"
                        ),
                    ),
                    (
                        "    Running state",
                        f"{'✓' if holder['running'] else '✗'} {holder['running_state']}",
                    ),
                    (
                        "    Final state",
                        f"{'✓' if holder['completed'] else '✗'} {holder['final_state']}",
                    ),
                    (
                        "    Allocated node",
                        (
                            f"{'✓' if holder['allocated_ok'] else '✗'} "
                            f"{holder['allocated_node']}"
                        ),
                    ),
                    (
                        "    Standard output",
                        f"{'✓' if holder['output_ok'] else '✗'} {holder['stdout']}",
                    ),
                    (
                        "    Error output",
                        f"{'✓' if holder['stderr_ok'] else '✗'} {holder['stderr']}",
                    ),
                ]
            )
        fields.extend(
            [
                ("Queued follower targets", follower_targets),
                ("  Job command", follower_command),
                (
                    "  Job submitted",
                    (
                        f"{'✓' if follower_submitted else '✗'} job ID "
                        f"{follower_id or 'missing'}"
                    ),
                ),
                (
                    "  Pending state observed",
                    (
                        f"{'✓' if pending else '✗'} {pending_state} | "
                        f"reason={pending_reason}"
                    ),
                ),
                (
                    "  Completed after saturation jobs released resources",
                    (
                        f"{'✓' if follower_completed else '✗'} "
                        f"{follower_final_record or 'unknown'}"
                    ),
                ),
                (
                    "  Allocated node",
                    (
                        f"{'✓' if allocated_row is not None else '✗'} "
                        f"{follower_accounting['allocated_node']}"
                    ),
                ),
                (
                    "  Standard output",
                    f"{'✓' if follower_output_ok else '✗'} {follower_stdout}",
                ),
                (
                    "  Error output",
                    f"{'✓' if follower_stderr_ok else '✗'} {follower_stderr}",
                ),
                (
                    "Final queue",
                    (
                        f"{'✓' if queue_empty else '✗'} "
                        f"{len(remaining_jobs)} active job(s)"
                    ),
                ),
                *[("  Remaining job", job) for job in remaining_jobs],
            ]
        )
        success = (
            all_holders_running
            and all(holder["success"] for holder in holders)
            and follower_success
            and queue_empty
        )
        failure_reasons = []
        if not all_holders_running:
            failure_reasons.append("not every saturation job reached RUNNING")
        if not all(holder["success"] for holder in holders):
            failure_reasons.append("one or more saturation jobs failed")
        if not pending:
            failure_reasons.append("the follower job was not observed pending")
        if not follower_success:
            failure_reasons.append("the follower job did not complete correctly")
        if not queue_empty:
            failure_reasons.append("the final Slurm queue was not empty")
        return runtime_result(
            success,
            summary,
            fields,
            "; ".join(failure_reasons),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
    finally:
        if control is not None:
            for job_id in jobs:
                try:
                    remote_command(
                        host,
                        control,
                        PXEBOOT_COMMANDS["slurm_cancel_job"] % job_id,
                    )
                except (OSError, RuntimeError, TypeError, ValueError):
                    pass
            for row in computes:
                for job_id in jobs:
                    try:
                        remote_command(
                            host,
                            row,
                            PXEBOOT_COMMANDS["slurm_cleanup_queue_job"]
                            % (job_id, job_id),
                        )
                    except (OSError, RuntimeError, TypeError, ValueError):
                        pass


def check_slurm_drain_queue_recovery(host):
    """Drain one compute node, observe a pending job, then restore the node."""
    summary = "Slurm drain, queue, and resume behavior"
    job_id = ""
    control = None
    compute = None
    try:
        if not marker_is_authorized("disruptive"):
            return _skip(
                summary,
                "Select the disruptive marker to authorize node draining",
            )
        _runtime, rows, control, _config = _context(host)
        computes = _compute_rows(rows)
        if not computes:
            return _skip(summary, "No Slurm compute nodes are mapped")
        compute = computes[0]
        node_name = compute["HOSTNAME"]
        drain = remote_command(
            host,
            control,
            PXEBOOT_COMMANDS["slurm_drain_node"] % (node_name, SLURM_DRAIN_REASON),
        )
        if drain.rc != 0:
            raise RuntimeError("The selected compute node could not be drained")
        submit = remote_command(
            host,
            control,
            PXEBOOT_COMMANDS["slurm_submit_drain_job"] % node_name,
        )
        parts = submit.stdout.strip().split("|", 1)
        if submit.rc == 0 and len(parts) == 2 and parts[0].isdigit():
            job_id = parts[0]
        state = parts[1].upper() if len(parts) == 2 else ""
        pending = submit.rc == 0 and state.startswith("PENDING")
        return runtime_result(
            pending,
            summary,
            [
                ("Drained node", node_name),
                ("Queued job state", state or "unknown"),
            ],
            "A job constrained to the drained node did not remain pending"
            if not pending
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
    finally:
        if control is not None and job_id:
            remote_command(
                host,
                control,
                PXEBOOT_COMMANDS["slurm_cancel_job"] % job_id,
            )
        if control is not None and compute is not None:
            remote_command(
                host,
                control,
                PXEBOOT_COMMANDS["slurm_resume_node"] % compute["HOSTNAME"],
            )


def check_slurm_openmpi_job(host):
    """Compile and run an MPI program through Slurm's PMIx launcher."""
    summary = "Slurm OpenMPI job"
    workspace = ""
    control = None
    try:
        gated = _require_functional(summary)
        if gated:
            return gated
        context, rows, control, config = _context(host)
        if not rows or not context["features"].get("openmpi", False):
            return _skip(summary, "OpenMPI is not selected in the active catalog")
        computes = _compute_rows(rows)
        if not computes:
            return _skip(summary, "No mapped Slurm compute node is available")
        targets = computes[: min(2, len(computes))]

        toolchains = []
        for row in targets:
            discovery = remote_command(host, row, PXEBOOT_COMMANDS["openmpi"])
            records = {
                match.group(1): match.group(2)
                for line in discovery.stdout.splitlines()
                if (match := _OPENMPI_RECORD_RE.fullmatch(line.strip()))
            }
            if discovery.rc != 0 or set(records) != {
                "OPENMPI_EXECUTABLE",
                "OPENMPI_COMPILER",
            }:
                raise RuntimeError(
                    f"OpenMPI toolchain discovery failed on {row['HOSTNAME']}"
                )
            toolchains.append(records)
        executable_paths = {record["OPENMPI_EXECUTABLE"] for record in toolchains}
        compiler_paths = {record["OPENMPI_COMPILER"] for record in toolchains}
        if len(executable_paths) != 1 or len(compiler_paths) != 1:
            raise RuntimeError("Mapped MPI nodes do not use one common toolchain")
        mpirun_path = executable_paths.pop()
        mpicc_path = compiler_paths.pop()
        mpi_prefix = str(Path(mpirun_path).parent.parent)
        mpi_bin = str(Path(mpi_prefix) / "bin")
        mpi_libraries = f"{mpi_prefix}/lib:{mpi_prefix}/lib64"
        stack_name = (
            "shared /hpc_tools OpenMPI"
            if mpi_prefix.startswith("/hpc_tools/")
            else "DOCA OpenMPI"
        )

        plugin_result = remote_command(
            host,
            control,
            PXEBOOT_COMMANDS["slurm_mpi_plugins"],
        )
        versions = sorted(
            set(re.findall(r"\bpmix_v\d+\b", plugin_result.stdout)),
            key=lambda value: int(value.rsplit("v", 1)[1]),
        )
        mpi_plugin = versions[-1] if versions else "pmix"
        if plugin_result.rc != 0 or "pmix" not in plugin_result.stdout:
            raise RuntimeError("Slurm does not expose a PMIx MPI plugin")

        storage = _shared_storage(context, config)
        workspace = (
            f"{storage['mount_point']}/.omnia_fvt/openmpi-{secrets.token_hex(8)}"
        )
        source_path = Path(__file__).resolve().parents[1] / "vars" / "slurm_mpi_smoke.c"
        if not source_path.is_file():
            raise FileNotFoundError(f"MPI smoke source is missing: {source_path}")
        encoded = base64.b64encode(source_path.read_bytes()).decode("ascii")
        remote_source = f"{workspace}/slurm_mpi_smoke.c"
        remote_binary = f"{workspace}/slurm_mpi_smoke"
        prepare = remote_command(
            host,
            control,
            "install -d -m 0700 "
            f"{shlex.quote(workspace)} && printf %s {shlex.quote(encoded)} | "
            f"base64 -d > {shlex.quote(remote_source)}",
        )
        if prepare.rc != 0:
            raise RuntimeError("Could not create the shared MPI test workspace")

        compile_script = (
            f"export PATH={shlex.quote(mpi_bin)}:$PATH; "
            f"export LD_LIBRARY_PATH={shlex.quote(mpi_libraries)}:"
            "${LD_LIBRARY_PATH:-}; "
            f"{shlex.quote(mpicc_path)} {shlex.quote(remote_source)} "
            f"-o {shlex.quote(remote_binary)}"
        )
        compile_result = remote_command(
            host,
            control,
            PXEBOOT_COMMANDS["openmpi_compile"]
            % (targets[0]["HOSTNAME"], shlex.quote(compile_script)),
        )
        if compile_result.rc != 0:
            raise RuntimeError(
                "OpenMPI compilation failed: "
                + re.sub(
                    r"\s+",
                    " ",
                    (compile_result.stderr or compile_result.stdout).strip(),
                )[:300]
            )

        node_list = ",".join(row["HOSTNAME"] for row in targets)
        export_value = (
            f"ALL,PATH={mpi_bin}:/usr/bin:/bin,"
            f"LD_LIBRARY_PATH={mpi_libraries},PMIX_MCA_gds=hash"
        )
        result = remote_command(
            host,
            control,
            PXEBOOT_COMMANDS["openmpi_job"]
            % (
                len(targets),
                len(targets),
                node_list,
                mpi_plugin,
                shlex.quote(export_value),
                shlex.quote(remote_binary),
            ),
        )
        rank_records = []
        for line in result.stdout.splitlines():
            match = _MPI_RESULT_RE.fullmatch(line.strip())
            if match:
                rank_records.append(
                    (
                        int(match.group(1)),
                        int(match.group(2)),
                        match.group(3).split(".", 1)[0],
                    )
                )
        expected_nodes = {row["HOSTNAME"] for row in targets}
        observed_nodes = {record[2] for record in rank_records}
        ranks = {record[0] for record in rank_records}
        expected_ranks = set(range(len(targets)))
        sizes = {record[1] for record in rank_records}
        stderr = re.sub(r"\s+", " ", result.stderr.strip())[:500]
        ok = (
            result.rc == 0
            and ranks == expected_ranks
            and sizes == {len(targets)}
            and observed_nodes == expected_nodes
            and not stderr
        )
        return runtime_result(
            ok,
            summary,
            [
                ("Submission node", control["HOSTNAME"]),
                ("MPI stack", f"{stack_name} | {mpi_prefix}"),
                ("MPI compiler", mpicc_path),
                ("Slurm MPI plugin", mpi_plugin),
                ("Requested ranks", len(targets)),
                ("Target nodes", ", ".join(sorted(expected_nodes))),
                ("Observed ranks", ", ".join(map(str, sorted(ranks))) or "none"),
                ("Observed nodes", ", ".join(sorted(observed_nodes)) or "none"),
                ("Standard error", stderr or "none"),
            ],
            re.sub(
                r"\s+",
                " ",
                (result.stderr or result.stdout or f"command rc={result.rc}").strip(),
            )[:500]
            if not ok
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
    finally:
        if (
            control is not None
            and workspace.startswith("/")
            and "/.omnia_fvt/openmpi-" in workspace
        ):
            remote_command(
                host,
                control,
                f"find {shlex.quote(workspace)} -mindepth 1 -delete 2>/dev/null; "
                f"rmdir {shlex.quote(workspace)} 2>/dev/null || true",
            )


def check_slurm_gpu_job(host):
    """Allocate one GPU through Slurm and query it inside the allocation."""
    summary = "Slurm GPU allocation"
    try:
        gated = _require_functional(summary)
        if gated:
            return gated
        _context_data, rows, control, _config = _context(host)
        gpu_rows = _gpu_rows(host, control, _compute_rows(rows))
        if not gpu_rows:
            return _skip(summary, "Slurm reports no GPU GRES on mapped compute nodes")
        gpu_row, gres, _count = gpu_rows[0]
        result = remote_command(
            host,
            control,
            PXEBOOT_COMMANDS["gpu_job"] % gpu_row["HOSTNAME"],
        )
        ok = result.rc == 0 and bool(result.stdout.strip())
        return runtime_result(
            ok,
            summary,
            [
                ("Target node", f"{gpu_row['HOSTNAME']} | {gpu_row['ADMIN_IP']}"),
                ("Scheduler GRES", gres),
                ("GPU allocation", "passed" if ok else "failed"),
                ("GPU output", result.stdout.strip() or "none"),
            ],
            "Slurm could not allocate and query a GPU" if not ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_slurm_gpu_memory_stress(host):
    """Compile and run a bounded CUDA memory-allocation probe through Slurm."""
    summary = "Slurm GPU memory stress"
    try:
        gated = _require_functional(summary)
        if gated:
            return gated
        _context_data, rows, control, _config = _context(host)
        if not _gpu_rows(host, control, _compute_rows(rows)):
            return _skip(summary, "Slurm reports no GPU GRES on mapped compute nodes")
        compiler = first_row(rows, SLURM_COMPILER_PREFIX) or control
        asset = Path(__file__).parents[1] / "assets" / "gpu_memory_stress.cu"
        payload = base64.b64encode(asset.read_bytes()).decode("ascii")
        if not re.fullmatch(r"[A-Za-z0-9+/=]+", payload):
            raise ValueError("The CUDA probe could not be encoded safely")
        result = remote_command(
            host,
            compiler,
            PXEBOOT_COMMANDS["gpu_memory_stress"] % payload,
        )
        ok = result.rc == 0 and "GPU_MEMORY_STRESS_OK" in result.stdout
        return runtime_result(
            ok,
            summary,
            [
                ("Submission node", compiler["HOSTNAME"]),
                ("CUDA compilation", "passed" if result.rc == 0 else "failed"),
                ("GPU memory probe", "passed" if ok else "failed"),
            ],
            "The bounded CUDA memory probe did not complete" if not ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
