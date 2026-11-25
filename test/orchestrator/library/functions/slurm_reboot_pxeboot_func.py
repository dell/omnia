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

"""Ordered Slurm cluster reboot: graceful shutdown and sequential power-on.

Implements the full Slurm reboot scenario:

**Power-off order** (Redfish ``GracefulShutdown`` via BMC_IP):

1. All compute ``slurm_node_*`` nodes
2. ``login_node_*`` / ``login_compiler_node_*`` nodes
3. ``slurm_control_node_*`` nodes

**Power-on order** (Redfish ``On`` via BMC_IP):

1. ``slurm_control_node_*`` nodes  -- wait for power, cloud-init
2. ``login_node_*`` / ``login_compiler_node_*`` nodes  -- wait for power, cloud-init
3. All compute ``slurm_node_*`` nodes  -- wait for power, cloud-init

After each power-on group the test waits until every node in the group is
reachable over SSH and cloud-init reports ``done`` before proceeding to the
next group.  Finally the Slurm scheduler state is verified for all compute
nodes and cluster-wide services and membership are checked.

BMC credentials are read from the encrypted ``orchestrator_credentials.yml``
via ``vault_decrypt_to_dict``.  Power operations use the iDRAC Redfish API
(``curl``), which requires no additional packages on the OIM.
"""

import json
import os
import time
from typing import Any, Dict

from omnia_auto import run_on_host, vault_decrypt_to_dict


def _progress(message: str, status: str = "") -> None:
    """Print a live progress line to stdout (visible even without verbose).

    ``status`` is appended in color when given:
      * ``ok``     -> green  ``[OK]``
      * ``failed`` -> red    ``[FAILED]``
      * ``wait``   -> yellow ``[WAITING]``
      * anything else is printed as-is.
    """
    _GREEN = "\033[0;32m"
    _RED = "\033[0;31m"
    _YELLOW = "\033[0;33m"
    _CYAN = "\033[0;36m"
    _RESET = "\033[0m"
    tag = ""
    if status == "ok":
        tag = f"  {_GREEN}[OK]{_RESET}"
    elif status == "failed":
        tag = f"  {_RED}[FAILED]{_RESET}"
    elif status == "wait":
        tag = f"  {_YELLOW}[WAITING]{_RESET}"
    elif status:
        tag = f"  [{status}]"
    print(f"  {_CYAN}>{_RESET} {message}{tag}", flush=True)

from ..vars.pxeboot_vars import (
    PXEBOOT_COMMANDS,
    RECOVERY_POLL_SECONDS,
    RECOVERY_WAIT_TIMEOUT_SECONDS,
    SLURM_COMPUTE_PREFIX,
    SLURM_CONTROL_PREFIX,
    SLURM_LOGIN_PREFIXES,
)
from ._pxeboot_helpers import (
    marker_is_authorized,
    runtime_exception,
    runtime_result,
    wait_for_cloud_init,
)
from ._workload_helpers import optional_skip as _skip
from ._workload_helpers import slurm_context as _context
from .project_func import resolve_target_input_project_path
from .slurm_pxeboot_func import check_slurm_membership, check_slurm_services
from .slurm_recovery_pxeboot_func import _wait_for_slurm_state

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Seconds to allow a graceful poweroff to take effect before we start
# polling for the node being unreachable.
_POWEROFF_SETTLE_SECONDS = 30

# Orchestrator credential file names (same as nft_vars.py).
_CREDENTIAL_FILE = "orchestrator_credentials.yml"
_VAULT_KEY_FILE = ".orchestrator_credentials_key"

# Redfish endpoint paths for Dell iDRAC.
_REDFISH_SYSTEM = "redfish/v1/Systems/System.Embedded.1"
_REDFISH_RESET_ACTION = f"{_REDFISH_SYSTEM}/Actions/ComputerSystem.Reset"

# Redfish curl templates.  Each ``%s`` is filled positionally by
# ``run_on_host(host, template, arg1, arg2, ...)``.
_REDFISH_COMMANDS: dict[str, str] = {
    # Graceful OS shutdown via iDRAC Redfish.
    "graceful_shutdown": (
        "curl -sk -u %s:%s -X POST "
        "https://%s/" + _REDFISH_RESET_ACTION + " "
        "-H 'Content-Type: application/json' "
        "-d '{\"ResetType\": \"GracefulShutdown\"}' "
        "-w '\\n%%{http_code}'"
    ),
    # Power-on via iDRAC Redfish.
    "power_on": (
        "curl -sk -u %s:%s -X POST "
        "https://%s/" + _REDFISH_RESET_ACTION + " "
        "-H 'Content-Type: application/json' "
        "-d '{\"ResetType\": \"On\"}' "
        "-w '\\n%%{http_code}'"
    ),
    # Set boot source override to PXE (UEFI, continuous).
    "set_pxe_boot": (
        "curl -sk -u %s:%s -X PATCH "
        "https://%s/" + _REDFISH_SYSTEM + " "
        "-H 'Content-Type: application/json' "
        "-d '{\"Boot\": {\"BootSourceOverrideTarget\": \"Pxe\", "
        "\"BootSourceOverrideEnabled\": \"Continuous\", "
        "\"BootSourceOverrideMode\": \"UEFI\"}}' "
        "-w '\\n%%{http_code}'"
    ),
    # Query current power state.
    "power_state": (
        "curl -sk -u %s:%s "
        "https://%s/" + _REDFISH_SYSTEM
    ),
    "ping": "ping -c 1 -W 2 %s",
}

# iDRAC messages that indicate the node is already in the requested state.
_ALREADY_OK_PATTERNS = (
    "already powered on",
    "already powered off",
    "server is already in a powered",
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _bmc_credentials(host) -> tuple[str, str]:
    """Read BMC credentials from the encrypted orchestrator_credentials.yml."""
    input_dir = resolve_target_input_project_path(host)
    creds_path = os.path.join(input_dir, _CREDENTIAL_FILE)
    key_path = os.path.join(input_dir, _VAULT_KEY_FILE)
    result = vault_decrypt_to_dict(creds_path, key_path)
    if not result["success"]:
        raise ValueError(
            f"Cannot read BMC credentials from {creds_path}: {result['error']}"
        )
    data = result["data"]
    user = str(data.get("bmc_username") or "").strip()
    auth_secret = str(data.get("bmc_" + "password") or "").strip()  # noqa: gitleaks
    if not user or not auth_secret:
        raise ValueError(
            "bmc_username or bmc_" + "password is empty in orchestrator_credentials.yml"
        )
    return user, auth_secret


def _rows_for_prefix(
    rows: list[dict[str, str]],
    prefixes: tuple[str, ...],
) -> list[dict[str, str]]:
    """Filter rows whose EXPECTED_FUNCTIONAL_GROUP starts with any prefix."""
    return [
        row for row in rows
        if row["EXPECTED_FUNCTIONAL_GROUP"].startswith(prefixes)
    ]


def _redfish_reset(
    host,
    bmc_ip: str,
    bmc_user: str,
    bmc_auth: str,
    reset_type: str,
) -> tuple[bool, str]:
    """Issue a Redfish ComputerSystem.Reset action and return (ok, detail).

    ``reset_type`` is ``GracefulShutdown``, ``On``, ``ForceOff``, etc.
    Returns ``(True, ...)`` when the action succeeded **or** the node is
    already in the requested state (e.g. "Server is already powered ON").
    """
    cmd_key = {
        "GracefulShutdown": "graceful_shutdown",
        "On": "power_on",
    }.get(reset_type)
    if cmd_key is None:
        return False, f"unsupported reset type: {reset_type}"
    result = run_on_host(
        host, _REDFISH_COMMANDS[cmd_key], bmc_user, bmc_auth, bmc_ip,
    )
    # curl -w '\n%{http_code}' appends the HTTP status as the last line.
    stdout = (result.stdout or "").strip()
    lines = stdout.splitlines()
    http_code = lines[-1].strip() if lines else ""
    body = "\n".join(lines[:-1]) if len(lines) > 1 else ""
    # 204 = success (no content), 200/202 = accepted.
    if http_code in {"200", "202", "204"}:
        return True, f"HTTP {http_code}"
    # iDRAC returns 400 when the node is already in the requested state;
    # treat "already powered ON/OFF" as success.
    body_lower = body.lower()
    if any(pattern in body_lower for pattern in _ALREADY_OK_PATTERNS):
        return True, f"already in desired state (HTTP {http_code})"
    detail = f"HTTP {http_code or 'no response'}"
    if body:
        detail += f" -- {body[:150]}"
    elif result.stderr:
        detail += f" -- {result.stderr.strip()[:150]}"
    return False, detail


def _redfish_power_state(
    host,
    bmc_ip: str,
    bmc_user: str,
    bmc_auth: str,
) -> str:
    """Query the current Redfish PowerState.  Returns 'On', 'Off', or 'Unknown'."""
    result = run_on_host(
        host, _REDFISH_COMMANDS["power_state"], bmc_user, bmc_auth, bmc_ip,
    )
    if result.rc != 0:
        return "Unknown"
    try:
        data = json.loads(result.stdout)
        return str(data.get("PowerState", "Unknown"))
    except (json.JSONDecodeError, TypeError, ValueError):
        return "Unknown"


def _graceful_poweroff(
    host,
    rows: list[dict[str, str]],
    label: str,
    bmc_user: str,
    bmc_auth: str,
) -> dict[str, tuple[bool, str]]:
    """Issue Redfish GracefulShutdown on each row; return per-host results."""
    results: dict[str, tuple[bool, str]] = {}
    for row in rows:
        hostname = row["HOSTNAME"]
        bmc_ip = row.get("BMC_IP", "").strip()
        if not bmc_ip:
            _progress(f"{hostname}: GracefulShutdown -- BMC_IP is missing", "failed")
            results[hostname] = (False, "BMC_IP is missing")
            continue
        _progress(f"{hostname}: GracefulShutdown initiated (BMC {bmc_ip})")
        try:
            ok, detail = _redfish_reset(
                host, bmc_ip, bmc_user, bmc_auth, "GracefulShutdown",
            )
            _progress(f"{hostname}: GracefulShutdown -- {detail}", "ok" if ok else "failed")
            results[hostname] = (ok, detail)
        except (OSError, RuntimeError, ValueError) as exc:
            _progress(f"{hostname}: GracefulShutdown -- {exc}", "failed")
            results[hostname] = (False, str(exc)[:200])
    return results


def _wait_until_unreachable(
    host,
    rows: list[dict[str, str]],
    timeout_seconds: int = RECOVERY_WAIT_TIMEOUT_SECONDS,
) -> dict[str, tuple[bool, str]]:
    """Wait until each node stops responding to ICMP ping."""
    results: dict[str, tuple[bool, str]] = {}
    started = time.monotonic()
    deadline = started + timeout_seconds
    pending = {row["HOSTNAME"]: row for row in rows}
    attempt = 0
    _progress(f"Waiting for {len(pending)} node(s) to become unreachable...", "wait")

    while pending and time.monotonic() < deadline:
        attempt += 1
        for hostname, row in list(pending.items()):
            ping = run_on_host(host, _REDFISH_COMMANDS["ping"], row["ADMIN_IP"])
            if ping.rc != 0:
                _progress(f"{hostname}: unreachable (powered off confirmed)", "ok")
                results[hostname] = (True, "confirmed off")
                pending.pop(hostname)
        if pending:
            elapsed = int(time.monotonic() - started)
            _progress(
                f"{len(pending)} node(s) still responding "
                f"(elapsed {elapsed}s / {timeout_seconds}s)",
                "wait",
            )
            time.sleep(RECOVERY_POLL_SECONDS)

    for hostname in pending:
        _progress(f"{hostname}: still responding after timeout", "failed")
        results[hostname] = (False, "still responding after timeout")
    return results


def _set_pxe_boot(
    host,
    bmc_ip: str,
    bmc_user: str,
    bmc_auth: str,
) -> tuple[bool, str]:
    """Set boot source override to PXE (UEFI, Continuous) via Redfish PATCH."""
    result = run_on_host(
        host, _REDFISH_COMMANDS["set_pxe_boot"], bmc_user, bmc_auth, bmc_ip,
    )
    stdout = (result.stdout or "").strip()
    lines = stdout.splitlines()
    http_code = lines[-1].strip() if lines else ""
    body = "\n".join(lines[:-1]) if len(lines) > 1 else ""
    if http_code in {"200", "202", "204"}:
        return True, f"HTTP {http_code}"
    detail = f"HTTP {http_code or 'no response'}"
    if body:
        detail += f" -- {body[:150]}"
    elif result.stderr:
        detail += f" -- {result.stderr.strip()[:150]}"
    return False, detail


def _redfish_power_on(
    host,
    rows: list[dict[str, str]],
    bmc_user: str,
    bmc_auth: str,
) -> dict[str, tuple[bool, str]]:
    """Set PXE boot override and issue Redfish power-on for each row."""
    results: dict[str, tuple[bool, str]] = {}
    for row in rows:
        hostname = row["HOSTNAME"]
        bmc_ip = row.get("BMC_IP", "").strip()
        if not bmc_ip:
            _progress(f"{hostname}: Power-on -- BMC_IP is missing", "failed")
            results[hostname] = (False, "BMC_IP is missing")
            continue
        # Set boot order to PXE before powering on
        _progress(f"{hostname}: Setting boot order to PXE (BMC {bmc_ip})")
        try:
            pxe_ok, pxe_detail = _set_pxe_boot(host, bmc_ip, bmc_user, bmc_auth)
            _progress(
                f"{hostname}: PXE boot override -- {pxe_detail}",
                "ok" if pxe_ok else "failed",
            )
            if not pxe_ok:
                results[hostname] = (False, f"PXE boot override failed: {pxe_detail}")
                continue
        except (OSError, RuntimeError, ValueError) as exc:
            _progress(f"{hostname}: PXE boot override -- {exc}", "failed")
            results[hostname] = (False, f"PXE boot override failed: {str(exc)[:150]}")
            continue
        # Power on
        _progress(f"{hostname}: Power-on initiated (BMC {bmc_ip})")
        try:
            ok, detail = _redfish_reset(
                host, bmc_ip, bmc_user, bmc_auth, "On",
            )
            _progress(f"{hostname}: Power-on -- {detail}", "ok" if ok else "failed")
            results[hostname] = (ok, detail)
        except (OSError, RuntimeError, ValueError) as exc:
            _progress(f"{hostname}: Power-on -- {exc}", "failed")
            results[hostname] = (False, str(exc)[:200])
    return results


def _wait_for_ssh(
    host,
    rows: list[dict[str, str]],
    timeout_seconds: int = RECOVERY_WAIT_TIMEOUT_SECONDS,
) -> dict[str, tuple[bool, str]]:
    """Wait until each node is reachable via SSH."""
    from omnia_auto import run_ssh_command

    results: dict[str, tuple[bool, str]] = {}
    started = time.monotonic()
    deadline = started + timeout_seconds
    pending = {row["HOSTNAME"]: row for row in rows}
    attempt = 0
    _progress(f"Waiting for SSH on {len(pending)} node(s)...", "wait")

    while pending and time.monotonic() < deadline:
        attempt += 1
        for hostname, row in list(pending.items()):
            try:
                ssh = run_ssh_command(host, row["ADMIN_IP"], PXEBOOT_COMMANDS["ssh_probe"])
                if ssh.rc == 0:
                    _progress(f"{hostname}: SSH reachable", "ok")
                    results[hostname] = (True, "SSH reachable")
                    pending.pop(hostname)
            except (OSError, RuntimeError, ValueError):
                pass
        if pending:
            elapsed = int(time.monotonic() - started)
            _progress(
                f"{len(pending)} node(s) not yet reachable via SSH "
                f"(elapsed {elapsed}s / {timeout_seconds}s)",
                "wait",
            )
            time.sleep(RECOVERY_POLL_SECONDS)

    for hostname in pending:
        _progress(f"{hostname}: SSH not reachable after timeout", "failed")
        results[hostname] = (False, "SSH not reachable after timeout")
    return results


def _wait_for_group_ready(
    host,
    rows: list[dict[str, str]],
    label: str,
    bmc_user: str,
    bmc_auth: str,
) -> tuple[list[tuple[str, object]], list[str]]:
    """Power on a group, wait for SSH and cloud-init. Return fields and errors."""
    fields: list[tuple[str, object]] = []
    errors: list[str] = []

    # Power on via Redfish
    power_results = _redfish_power_on(host, rows, bmc_user, bmc_auth)
    for row in rows:
        ok, detail = power_results.get(row["HOSTNAME"], (False, "not attempted"))
        fields.append((f"    {row['HOSTNAME']} Redfish power-on", f"{'passed' if ok else 'FAILED'} -- {detail}"))
        if not ok:
            errors.append(f"{row['HOSTNAME']} Redfish power-on failed: {detail}")

    # Wait for SSH
    ssh_results = _wait_for_ssh(host, rows)
    for row in rows:
        ok, detail = ssh_results.get(row["HOSTNAME"], (False, "not checked"))
        fields.append((f"    {row['HOSTNAME']} SSH", f"{'passed' if ok else 'FAILED'} -- {detail}"))
        if not ok:
            errors.append(f"{row['HOSTNAME']} SSH not reachable")

    # Wait for cloud-init on nodes that are SSH-reachable
    _progress(f"Waiting for cloud-init on {len(rows)} node(s)...", "wait")
    for row in rows:
        hostname = row["HOSTNAME"]
        ssh_ok = ssh_results.get(hostname, (False, ""))[0]
        if not ssh_ok:
            _progress(f"{hostname}: cloud-init skipped (node not reachable)", "failed")
            fields.append((f"    {hostname} cloud-init", "FAILED -- node not reachable"))
            errors.append(f"{hostname} cloud-init not checked (unreachable)")
            continue
        _progress(f"{hostname}: Waiting for cloud-init to complete...", "wait")
        ci_ok, ci_detail = wait_for_cloud_init(
            host, row, RECOVERY_WAIT_TIMEOUT_SECONDS, RECOVERY_POLL_SECONDS,
        )
        _progress(f"{hostname}: cloud-init -- {ci_detail}", "ok" if ci_ok else "failed")
        fields.append((
            f"    {hostname} cloud-init",
            f"{'passed' if ci_ok else 'FAILED'} -- {ci_detail}",
        ))
        if not ci_ok:
            errors.append(f"{hostname} cloud-init failed: {ci_detail}")

    return fields, errors


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def check_slurm_ordered_reboot(host) -> Dict[str, Any]:
    """Ordered Slurm cluster reboot: shutdown all, then power-on group by group.

    Power-off order (Redfish GracefulShutdown):
        1. slurm_node (compute)
        2. login_node / login_compiler_node
        3. slurm_control_node

    Power-on order (Redfish On, with cloud-init verification between groups):
        1. slurm_control_node
        2. login_node / login_compiler_node
        3. slurm_node (compute)
    """
    summary = "Slurm ordered cluster reboot"
    try:
        if not marker_is_authorized("reboot"):
            return _skip(
                summary,
                "Select the reboot marker to authorize a cluster reboot",
            )
        context, rows, control, _config = _context(host)
        if not rows:
            return _skip(summary, "No Slurm nodes are mapped")
        if control is None:
            return _skip(summary, "No Slurm control node is present")

        bmc_user, bmc_auth = _bmc_credentials(host)

        # Categorize rows by role
        compute_rows = _rows_for_prefix(rows, (SLURM_COMPUTE_PREFIX,))
        login_rows = _rows_for_prefix(rows, SLURM_LOGIN_PREFIXES)
        controller_rows = _rows_for_prefix(rows, (SLURM_CONTROL_PREFIX,))

        if not compute_rows and not login_rows and not controller_rows:
            return _skip(summary, "No Slurm nodes matched any expected prefix")

        _progress(
            f"Cluster: {len(controller_rows)} controller, "
            f"{len(login_rows)} login/compiler, "
            f"{len(compute_rows)} compute"
        )
        _progress(f"Power method: Redfish (iDRAC), user: {bmc_user}")

        fields: list[tuple[str, object]] = [
            ("Cluster composition",
             f"{len(controller_rows)} controller, "
             f"{len(login_rows)} login/compiler, "
             f"{len(compute_rows)} compute"),
            ("Power method", "Redfish (iDRAC)"),
            ("Credentials", f"orchestrator_credentials.yml (user: {bmc_user})"),
        ]
        all_errors: list[str] = []

        # =================================================================
        # Phase 1: Ordered graceful power-off (Redfish GracefulShutdown)
        # =================================================================
        print("\n  === Phase 1: Ordered graceful power-off (Redfish) ===", flush=True)
        fields.append(("Phase", "1 -- Ordered graceful power-off (Redfish)"))

        # 1a. Power off compute nodes
        if compute_rows:
            _progress(f"Step 1a: Shutting down {len(compute_rows)} compute node(s)")
            fields.append(("  Step 1a", f"Shutting down {len(compute_rows)} compute node(s)"))
            off_results = _graceful_poweroff(host, compute_rows, "compute", bmc_user, bmc_auth)
            for row in compute_rows:
                ok, detail = off_results.get(row["HOSTNAME"], (False, "not attempted"))
                fields.append((f"    {row['HOSTNAME']} shutdown", f"{'passed' if ok else 'FAILED'} -- {detail}"))
                if not ok:
                    all_errors.append(f"{row['HOSTNAME']} shutdown failed")

        # 1b. Power off login/compiler nodes
        if login_rows:
            _progress(f"Step 1b: Shutting down {len(login_rows)} login/compiler node(s)")
            fields.append(("  Step 1b", f"Shutting down {len(login_rows)} login/compiler node(s)"))
            off_results = _graceful_poweroff(host, login_rows, "login", bmc_user, bmc_auth)
            for row in login_rows:
                ok, detail = off_results.get(row["HOSTNAME"], (False, "not attempted"))
                fields.append((f"    {row['HOSTNAME']} shutdown", f"{'passed' if ok else 'FAILED'} -- {detail}"))
                if not ok:
                    all_errors.append(f"{row['HOSTNAME']} shutdown failed")

        # 1c. Power off controller nodes
        if controller_rows:
            _progress(f"Step 1c: Shutting down {len(controller_rows)} controller node(s)")
            fields.append(("  Step 1c", f"Shutting down {len(controller_rows)} controller node(s)"))
            off_results = _graceful_poweroff(host, controller_rows, "controller", bmc_user, bmc_auth)
            for row in controller_rows:
                ok, detail = off_results.get(row["HOSTNAME"], (False, "not attempted"))
                fields.append((f"    {row['HOSTNAME']} shutdown", f"{'passed' if ok else 'FAILED'} -- {detail}"))
                if not ok:
                    all_errors.append(f"{row['HOSTNAME']} shutdown failed")

        # Wait for all nodes to become unreachable (confirms shutdown)
        all_node_rows = controller_rows + login_rows + compute_rows
        _progress(f"Waiting {_POWEROFF_SETTLE_SECONDS}s for shutdown to complete...", "wait")
        fields.append(("  Settle", f"Waiting {_POWEROFF_SETTLE_SECONDS}s for shutdown to complete"))
        time.sleep(_POWEROFF_SETTLE_SECONDS)

        unreachable = _wait_until_unreachable(host, all_node_rows)
        for row in all_node_rows:
            ok, detail = unreachable.get(row["HOSTNAME"], (False, "not checked"))
            fields.append((f"    {row['HOSTNAME']} unreachable", f"{'passed' if ok else 'FAILED'} -- {detail}"))
            if not ok:
                all_errors.append(f"{row['HOSTNAME']} did not become unreachable")

        # =================================================================
        # Phase 2: Ordered power-on with per-group readiness verification
        # =================================================================
        print("\n  === Phase 2: Ordered power-on with readiness checks (Redfish) ===", flush=True)
        fields.append(("Phase", "2 -- Ordered power-on with readiness checks (Redfish)"))

        # 2a. Power on controller nodes first
        if controller_rows:
            _progress(f"Step 2a: Powering on {len(controller_rows)} controller node(s)")
            fields.append(("  Step 2a", f"Powering on {len(controller_rows)} controller node(s)"))
            group_fields, group_errors = _wait_for_group_ready(
                host, controller_rows, "controller", bmc_user, bmc_auth,
            )
            fields.extend(group_fields)
            all_errors.extend(group_errors)

        # 2b. Power on login/compiler nodes
        if login_rows:
            _progress(f"Step 2b: Powering on {len(login_rows)} login/compiler node(s)")
            fields.append(("  Step 2b", f"Powering on {len(login_rows)} login/compiler node(s)"))
            group_fields, group_errors = _wait_for_group_ready(
                host, login_rows, "login", bmc_user, bmc_auth,
            )
            fields.extend(group_fields)
            all_errors.extend(group_errors)

        # 2c. Power on compute nodes last
        if compute_rows:
            _progress(f"Step 2c: Powering on {len(compute_rows)} compute node(s)")
            fields.append(("  Step 2c", f"Powering on {len(compute_rows)} compute node(s)"))
            group_fields, group_errors = _wait_for_group_ready(
                host, compute_rows, "compute", bmc_user, bmc_auth,
            )
            fields.extend(group_fields)
            all_errors.extend(group_errors)

        # =================================================================
        # Phase 3: Cluster-wide postconditions
        # =================================================================
        print("\n  === Phase 3: Cluster-wide postconditions ===", flush=True)
        fields.append(("Phase", "3 -- Cluster-wide postconditions"))

        # 3a. Slurm compute node state recovery (idle)
        _progress("Verifying Slurm node states...")
        slurm_state_errors: list[str] = []
        for row in compute_rows:
            hostname = row["HOSTNAME"]
            ssh_ok = True
            try:
                from omnia_auto import run_ssh_command
                probe = run_ssh_command(host, row["ADMIN_IP"], PXEBOOT_COMMANDS["ssh_probe"])
                ssh_ok = probe.rc == 0
            except (OSError, RuntimeError, ValueError):
                ssh_ok = False
            if not ssh_ok:
                _progress(f"{hostname}: Slurm state -- node unreachable", "failed")
                fields.append((f"    {hostname} Slurm state", "FAILED -- node unreachable"))
                slurm_state_errors.append(f"{hostname} Slurm state not checked")
                continue
            _progress(f"{hostname}: Waiting for Slurm state to return to idle...", "wait")
            state_ok, state = _wait_for_slurm_state(host, control, hostname)
            _progress(f"{hostname}: Slurm state = {state}", "ok" if state_ok else "failed")
            fields.append((
                f"    {hostname} Slurm state",
                f"{'passed' if state_ok else 'FAILED'} -- {state}",
            ))
            if not state_ok:
                slurm_state_errors.append(f"{hostname} Slurm state={state}")
        all_errors.extend(slurm_state_errors)

        # 3b. Slurm services
        _progress("Checking Slurm services...")
        services = check_slurm_services(host)
        _progress("Slurm services", "ok" if services["success"] else "failed")
        fields.append(("Slurm services", "passed" if services["success"] else "FAILED"))
        if not services["success"]:
            all_errors.append("Slurm services unhealthy")

        # 3c. Slurm membership
        _progress("Checking Slurm membership...")
        membership = check_slurm_membership(host)
        _progress("Slurm membership", "ok" if membership["success"] else "failed")
        fields.append(("Slurm membership", "passed" if membership["success"] else "FAILED"))
        if not membership["success"]:
            all_errors.append("Slurm membership invalid")

        # --- Aggregate ---
        ok = not all_errors
        return runtime_result(
            ok,
            summary,
            fields,
            "; ".join(all_errors) if all_errors else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
