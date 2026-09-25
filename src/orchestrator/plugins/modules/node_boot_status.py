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

"""Report fresh-boot and cloud-init state for one provisioned node."""

from __future__ import annotations

import json
import math
import os
import re
import time
from typing import Any

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r"""
---
module: node_boot_status
short_description: Verify a fresh PXE boot and cloud-init completion
description:
  - Reads the local node uptime and verifies that it booted after a supplied
    PXE request epoch.
  - Reads structured and human-readable cloud-init status without modifying
    the node.
  - Classifies pending, successful, benign-degraded, and failed cloud-init
    states for the Omnia PXE workflow.
options:
  pxe_start_epoch:
    description: Epoch timestamp recorded before the current PXE request.
    type: int
    required: true
author:
  - Dell Omnia Team
"""

EXAMPLES = r"""
- name: Inspect a node after PXE boot
  node_boot_status:
    pxe_start_epoch: 1789723000
  register: node_boot_result
"""

RETURN = r"""
terminal:
  description: Whether polling should stop for this node.
  type: bool
  returned: always
state:
  description: Omnia node-verification state.
  type: str
  returned: always
detail:
  description: Human-readable verification detail.
  type: str
  returned: always
boot:
  description: Fresh-boot calculation from local node uptime.
  type: dict
  returned: always
cloud_init:
  description: Structured cloud-init status fields.
  type: dict
  returned: always
"""

_CLOUD_INIT_PATH = "/usr/bin/cloud-init"
_MAX_COMMAND_OUTPUT_BYTES = 131072
_MAX_DETAIL_CHARACTERS = 1000
_EMPTY_CLOUD_CONFIG_TEXT = "empty cloud config"


def _read_uptime_seconds() -> int:
    """Return whole seconds from the kernel uptime interface."""
    with open("/proc/uptime", encoding="ascii") as uptime_file:
        raw_uptime = uptime_file.read(128).split(maxsplit=1)[0]
    uptime = float(raw_uptime)
    if not math.isfinite(uptime) or uptime < 0:
        raise ValueError("/proc/uptime did not contain a non-negative value")
    return int(uptime)


def _run_cloud_init(
    module: AnsibleModule, *arguments: str
) -> tuple[int, str, str]:
    """Run a fixed cloud-init command through Ansible without a shell."""
    return module.run_command(
        [_CLOUD_INIT_PATH, *arguments],
        check_rc=False,
        use_unsafe_shell=False,
    )


def _bounded_output(stdout: str, stderr: str) -> str:
    """Combine and bound command output used for status diagnostics."""
    output = "\n".join(part for part in (stdout, stderr) if part)
    return output[:_MAX_COMMAND_OUTPUT_BYTES]


def _status_field(output: str, field: str) -> str:
    """Read one field from ``cloud-init status --long`` output."""
    prefix = f"{field}:"
    for line in output.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return "unknown"


def _cloud_init_json(output: str) -> dict[str, Any]:
    """Parse a bounded cloud-init JSON object, returning safe defaults."""
    try:
        parsed = json.loads(output[:_MAX_COMMAND_OUTPUT_BYTES])
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _normalise_cloud_init(
    payload: dict[str, Any], status: str, extended_status: str
) -> dict[str, Any]:
    """Return the stable cloud-init report contract used by Omnia."""
    errors = payload.get("errors")
    recoverable_errors = payload.get("recoverable_errors")
    return {
        "status": payload.get("status", status),
        "extended_status": payload.get("extended_status", extended_status),
        "boot_status_code": payload.get("boot_status_code", ""),
        "errors": errors if isinstance(errors, list) else [],
        "recoverable_errors": (
            recoverable_errors if isinstance(recoverable_errors, dict) else {}
        ),
    }


def _is_benign_degraded(cloud_init: dict[str, Any]) -> bool:
    """Accept only OpenCHAMI's known empty user-data warning."""
    messages: list[str] = []
    for entries in cloud_init["recoverable_errors"].values():
        values = entries if isinstance(entries, list) else [entries]
        messages.extend(str(value) for value in values)
    return (
        not cloud_init["errors"]
        and bool(messages)
        and all(_EMPTY_CLOUD_CONFIG_TEXT in message for message in messages)
    )


def _detail(output: str) -> str:
    """Flatten and bound human-readable cloud-init status output."""
    flattened = re.sub(r"[\t ]+", " ", output.replace("\r", "").replace("\n", ";"))
    return flattened[:_MAX_DETAIL_CHARACTERS] or "cloud-init returned no status output"


def _empty_cloud_init(status: str = "unknown") -> dict[str, Any]:
    """Return the stable cloud-init report shape for unavailable status."""
    return {
        "status": status,
        "extended_status": status,
        "boot_status_code": "",
        "errors": [],
        "recoverable_errors": {},
    }


def _classify_cloud_init(
    module: AnsibleModule,
) -> tuple[bool, str, str, dict[str, Any]]:
    """Return terminal flag, state, detail, and structured cloud-init data."""
    if not os.path.isfile(_CLOUD_INIT_PATH) or not os.access(_CLOUD_INIT_PATH, os.X_OK):
        return (
            True,
            "cloud_init_error",
            "cloud-init command is not installed",
            _empty_cloud_init("not_installed"),
        )

    try:
        _, long_stdout, long_stderr = _run_cloud_init(module, "status", "--long")
        _, json_stdout, _ = _run_cloud_init(
            module, "status", "--format", "json"
        )
    except OSError as error:
        return (
            True,
            "cloud_init_error",
            f"cloud-init status could not run: {error}",
            _empty_cloud_init(),
        )

    long_output = _bounded_output(long_stdout, long_stderr)
    status = _status_field(long_output, "status")
    extended_status = _status_field(long_output, "extended_status")
    payload = _cloud_init_json(json_stdout)
    cloud_init = _normalise_cloud_init(payload, status, extended_status)

    terminal = False
    state = "cloud_init_pending"
    detail = _detail(long_output)
    if status == "done" and extended_status.startswith("degraded"):
        terminal = True
        state = "cloud_init_error"
        if _is_benign_degraded(cloud_init):
            state = "success"
            # This warning is an expected OpenCHAMI condition and already
            # participates in the success classification above.  Do not carry
            # it into the persistent status report; retain all other warnings.
            cloud_init.pop("recoverable_errors", None)
            detail = "Fresh PXE boot completed and cloud-init status is done"
    elif status == "done":
        terminal = True
        state = "success"
        detail = "Fresh PXE boot completed and cloud-init status is done"
    elif status in {"error", "degraded", "disabled", "not_installed"}:
        terminal = True
        state = "cloud_init_error"

    return terminal, state, detail, cloud_init


def main() -> None:
    """Run node-local PXE boot verification and return structured state."""
    module = AnsibleModule(
        argument_spec={
            "pxe_start_epoch": {"type": "int", "required": True},
        },
        supports_check_mode=True,
    )

    pxe_start_epoch = module.params["pxe_start_epoch"]
    if pxe_start_epoch <= 0:
        module.fail_json(msg="pxe_start_epoch must be a positive integer")

    try:
        uptime_seconds = _read_uptime_seconds()
    except (OSError, ValueError) as error:
        module.exit_json(
            changed=False,
            terminal=True,
            state="boot_time_unavailable",
            detail=f"SSH succeeded but /proc/uptime could not be read: {error}",
            boot={"fresh": False, "uptime_seconds": None, "boot_epoch": None},
            cloud_init={},
        )

    boot_epoch = int(time.time()) - uptime_seconds
    boot = {
        "fresh": boot_epoch >= pxe_start_epoch,
        "uptime_seconds": uptime_seconds,
        "boot_epoch": boot_epoch,
    }
    if not boot["fresh"]:
        module.exit_json(
            changed=False,
            terminal=False,
            state="stale_boot",
            detail="Node boot predates the current PXE request",
            boot=boot,
            cloud_init={},
        )

    terminal, state, detail, cloud_init = _classify_cloud_init(module)
    module.exit_json(
        changed=False,
        terminal=terminal,
        state=state,
        detail=detail,
        boot=boot,
        cloud_init=cloud_init,
    )


if __name__ == "__main__":
    main()
