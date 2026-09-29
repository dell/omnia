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

"""Explicitly authorized Apptainer compute-node reboot verification."""

import time

from ..vars.pxeboot_vars import (
    PXEBOOT_COMMANDS,
    RECOVERY_POLL_SECONDS,
    RECOVERY_WAIT_TIMEOUT_SECONDS,
)
from ._apptainer_helpers import (
    apptainer_context,
    command_error,
    primary_image,
    quoted_image,
    run_targeted_container,
    safe_node_name,
)
from ._pxeboot_helpers import (
    remote_command,
    report_poll_progress,
    runtime_exception,
    runtime_result,
    wait_for_cloud_init,
)
from ._workload_helpers import optional_skip, require_marker

_RECOVERY_STATE: dict[str, object] = {}


def _wait_for_new_boot(host, row, previous_boot_id):
    started = time.monotonic()
    deadline = started + RECOVERY_WAIT_TIMEOUT_SECONDS
    attempt = 0
    while time.monotonic() < deadline:
        attempt += 1
        try:
            result = remote_command(host, row, PXEBOOT_COMMANDS["node_boot_id"])
        except (OSError, RuntimeError, ValueError):
            result = None
        if result is not None:
            current = result.stdout.strip()
            if result.rc == 0 and current and current != previous_boot_id:
                return True, current
        report_poll_progress(
            f"{row['HOSTNAME']} reboot",
            attempt,
            started,
            RECOVERY_WAIT_TIMEOUT_SECONDS,
            "waiting for a new kernel boot identity",
        )
        time.sleep(RECOVERY_POLL_SECONDS)
    return False, ""


def _wait_for_scheduler(host, control, node_name):
    started = time.monotonic()
    deadline = started + RECOVERY_WAIT_TIMEOUT_SECONDS
    state = "missing"
    attempt = 0
    while time.monotonic() < deadline:
        attempt += 1
        result = remote_command(
            host,
            control,
            PXEBOOT_COMMANDS["slurm_node_state"] % safe_node_name(node_name),
        )
        state = result.stdout.strip().lower().split("+", 1)[0].rstrip("*~#$@!%^")
        if result.rc == 0 and state == "idle":
            return True, state
        report_poll_progress(
            f"{node_name} Slurm scheduler recovery",
            attempt,
            started,
            RECOVERY_WAIT_TIMEOUT_SECONDS,
            f"state={state}",
        )
        time.sleep(RECOVERY_POLL_SECONDS)
    return False, state


def _prepare_recovery(host):
    if _RECOVERY_STATE:
        return _RECOVERY_STATE
    gated = require_marker(
        "Apptainer compute-node reboot",
        "disruptive",
        "Select reboot or disruptive to authorize a compute-node reboot",
    )
    if gated:
        _RECOVERY_STATE.update({"skipped_result": gated})
        return _RECOVERY_STATE
    context, _rows, control, computes, _config = apptainer_context(host)
    if not computes:
        _RECOVERY_STATE.update(
            {
                "skipped_result": optional_skip(
                    "Apptainer compute-node reboot",
                    "No Slurm compute nodes are mapped",
                )
            }
        )
        return _RECOVERY_STATE
    row = computes[0]
    image = primary_image(host, row)
    before_checksum = remote_command(
        host,
        row,
        PXEBOOT_COMMANDS["apptainer_checksum"] % quoted_image(image["path"]),
    )
    before_mount = remote_command(host, row, PXEBOOT_COMMANDS["apptainer_shared_mount"])
    before_boot = remote_command(host, row, PXEBOOT_COMMANDS["node_boot_id"])
    previous_boot_id = before_boot.stdout.strip()
    if (
        before_checksum.rc != 0
        or before_mount.rc != 0
        or before_boot.rc != 0
        or not previous_boot_id
    ):
        raise RuntimeError("Apptainer reboot preconditions are invalid")
    reboot = remote_command(host, row, PXEBOOT_COMMANDS["node_reboot"])
    if reboot.rc not in {0, 255}:
        raise RuntimeError("Compute-node reboot request failed")
    new_boot, current_boot_id = _wait_for_new_boot(host, row, previous_boot_id)
    cloud_ok = False
    cloud_detail = "node did not return"
    scheduler_ok = False
    scheduler_state = "not checked"
    if new_boot:
        cloud_ok, cloud_detail = wait_for_cloud_init(
            host,
            row,
            RECOVERY_WAIT_TIMEOUT_SECONDS,
            RECOVERY_POLL_SECONDS,
        )
        scheduler_ok, scheduler_state = _wait_for_scheduler(
            host, control, row["HOSTNAME"]
        )
    _RECOVERY_STATE.update(
        {
            "context": context,
            "control": control,
            "row": row,
            "image": image,
            "before_checksum": before_checksum.stdout.split()[0],
            "before_mount": before_mount.stdout.strip(),
            "previous_boot_id": previous_boot_id,
            "current_boot_id": current_boot_id,
            "new_boot": new_boot,
            "cloud_ok": cloud_ok,
            "cloud_detail": cloud_detail,
            "scheduler_ok": scheduler_ok,
            "scheduler_state": scheduler_state,
        }
    )
    return _RECOVERY_STATE


def _base_fields(state):
    row = state["row"]
    return [
        ("Rebooted compute", f"{row['HOSTNAME']} | {row['ADMIN_IP']}"),
        ("New kernel boot", state["new_boot"]),
        ("Cloud-init", state["cloud_detail"]),
        ("Slurm state", state["scheduler_state"]),
    ]


def check_apptainer_reboot_storage(host):
    """Verify /hpc_tools and the selected SIF survive a real compute reboot."""
    summary = "Apptainer storage after compute reboot"
    try:
        state = _prepare_recovery(host)
        if "skipped_result" in state:
            return state["skipped_result"]
        row = state["row"]
        image = state["image"]
        after_mount = remote_command(
            host, row, PXEBOOT_COMMANDS["apptainer_shared_mount"]
        )
        after_checksum = remote_command(
            host,
            row,
            PXEBOOT_COMMANDS["apptainer_checksum"] % quoted_image(image["path"]),
        )
        checksum = (
            after_checksum.stdout.split()[0]
            if after_checksum.rc == 0 and after_checksum.stdout.split()
            else ""
        )
        mount_preserved = (
            after_mount.rc == 0 and after_mount.stdout.strip() == state["before_mount"]
        )
        image_preserved = checksum == state["before_checksum"]
        ok = (
            state["new_boot"]
            and state["cloud_ok"]
            and state["scheduler_ok"]
            and mount_preserved
            and image_preserved
        )
        return runtime_result(
            ok,
            summary,
            [
                *_base_fields(state),
                ("Shared mount preserved", mount_preserved),
                ("SIF checksum preserved", image_preserved),
                ("Image", image["name"]),
            ],
            "Shared Apptainer storage did not recover after reboot" if not ok else "",
        )
    except (FileNotFoundError, OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_apptainer_reboot_job(host):
    """Run an exact-node Apptainer Slurm job after the compute reboot."""
    summary = "Apptainer job after compute reboot"
    try:
        state = _prepare_recovery(host)
        if "skipped_result" in state:
            return state["skipped_result"]
        result = run_targeted_container(
            host,
            state["control"],
            state["row"],
            state["image"]["path"],
        )
        ok = (
            state["new_boot"]
            and state["cloud_ok"]
            and state["scheduler_ok"]
            and result["success"]
        )
        return runtime_result(
            ok,
            summary,
            [
                *_base_fields(state),
                ("Job ID", result["job_id"]),
                ("Container output", result["output"]),
            ],
            result["error"] if not ok else "",
        )
    except (FileNotFoundError, OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_apptainer_reboot_artifacts(host):
    """Verify the downloader remains executable and Pulp-only after reboot."""
    summary = "Apptainer download artifacts after compute reboot"
    try:
        state = _prepare_recovery(host)
        if "skipped_result" in state:
            return state["skipped_result"]
        row = state["row"]
        artifacts = remote_command(
            host, row, PXEBOOT_COMMANDS["apptainer_shared_artifacts"]
        )
        policy = remote_command(host, row, PXEBOOT_COMMANDS["apptainer_pulp_policy"])
        ok = (
            state["new_boot"]
            and state["cloud_ok"]
            and state["scheduler_ok"]
            and artifacts.rc == 0
            and policy.rc == 0
        )
        return runtime_result(
            ok,
            summary,
            [
                *_base_fields(state),
                (
                    "Download artifacts",
                    "valid" if artifacts.rc == 0 else command_error(artifacts),
                ),
                (
                    "Pulp-only policy",
                    "valid" if policy.rc == 0 else command_error(policy),
                ),
            ],
            "Apptainer download artifacts are invalid after reboot" if not ok else "",
        )
    except (FileNotFoundError, OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
