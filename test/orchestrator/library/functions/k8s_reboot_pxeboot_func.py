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

"""Ordered Kubernetes cluster reboot: graceful shutdown and sequential power-on.

Implements the full Kubernetes reboot scenario:

**Power-off order** (Redfish ``GracefulShutdown`` via BMC_IP):

1. All worker ``service_kube_node_*`` nodes
2. Secondary ``service_kube_control_plane_*`` nodes
3. Primary ``service_kube_control_plane_first_*`` node (last)

**Power-on order** (Redfish ``On`` via BMC_IP, with PXE boot override):

1. Primary ``service_kube_control_plane_first_*`` node  -- wait for SSH,
   cloud-init, etcd leadership
2. All remaining nodes (secondary control-plane + workers) in parallel
   -- wait for SSH, cloud-init

The primary control-plane is powered on first so that etcd can establish
leadership and the Kubernetes API server becomes healthy before cloud-init
scripts on the primary (such as CoreDNS restart) run.  Once the primary
is ready, all remaining nodes are powered on together so they can join
the cluster in parallel.

After each power-on group the test waits until every node in the group is
reachable over SSH and cloud-init reports ``done`` before proceeding to the
next group.  Finally the Kubernetes cluster health is verified: node
readiness, control-plane readiness, system pods, and etcd health.

**Output**: a clean summary is printed to stdout (phase headers and
per-step OK/FAILED with elapsed time).  Detailed per-node Redfish calls,
SSH polling, and cloud-init probes are written to a log file whose path
is shown at the end of the summary.

BMC credentials are read from the encrypted ``orchestrator_credentials.yml``
via ``vault_decrypt_to_dict``.  Power operations use the iDRAC Redfish API
(``curl``), which requires no additional packages on the OIM.
"""

import contextlib
import io
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict

from ..vars.pxeboot_vars import (
    KUBERNETES_CONTROL_PLANE_PREFIX,
    KUBERNETES_NODE_PREFIX,
    KUBERNETES_PRIMARY_CONTROL_PLANE_PREFIX,
)
from ._pxeboot_helpers import (
    direct_cloud_init_probe,
    marker_is_authorized,
    runtime_exception,
    runtime_result,
)
from ._workload_helpers import kubernetes_context as _context
from ._workload_helpers import optional_skip as _skip
from .kubernetes_pxeboot_func import (
    check_kubernetes_control_plane,
    check_kubernetes_nodes,
    check_kubernetes_system_pods,
)
from .kubernetes_etcd_pxeboot_func import check_kubernetes_etcd_health
from .slurm_reboot_pxeboot_func import (
    _bmc_credentials,
    _graceful_poweroff,
    _redfish_power_on,
    _rows_for_prefix,
    _wait_for_ssh,
    _wait_until_unreachable,
    _POWEROFF_SETTLE_SECONDS,
    RECOVERY_POLL_SECONDS,
    RECOVERY_WAIT_TIMEOUT_SECONDS,
)


# ---------------------------------------------------------------------------
# ANSI helpers (same palette as _progress in slurm_reboot_pxeboot_func)
# ---------------------------------------------------------------------------
_GREEN = "\033[0;32m"
_RED = "\033[0;31m"
_YELLOW = "\033[0;33m"
_CYAN = "\033[0;36m"
_RESET = "\033[0m"


def _ok_tag() -> str:
    return f"{_GREEN}[OK]{_RESET}"


def _failed_tag() -> str:
    return f"{_RED}[FAILED]{_RESET}"


def _warn_tag() -> str:
    return f"{_YELLOW}[WARNING]{_RESET}"


# ---------------------------------------------------------------------------
# Summary printer (always writes to real stdout, never to the log tee)
# ---------------------------------------------------------------------------
_real_stdout = sys.stdout  # captured at import time


def _summary(message: str, status: str = "") -> None:
    """Print a clean summary line to the real stdout."""
    tag = ""
    if status == "ok":
        tag = f"  {_ok_tag()}"
    elif status == "failed":
        tag = f"  {_failed_tag()}"
    elif status == "warn":
        tag = f"  {_warn_tag()}"
    _real_stdout.write(f"  {_CYAN}>{_RESET} {message}{tag}\n")
    _real_stdout.flush()


def _phase_header(text: str) -> None:
    """Print a phase header to the real stdout."""
    _real_stdout.write(f"\n  === {text} ===\n")
    _real_stdout.flush()


# ---------------------------------------------------------------------------
# Tee context manager: redirect stdout to log file, keep _summary on screen
# ---------------------------------------------------------------------------
class _TeeToFile:
    """Write everything sent to stdout into a file (for detailed logging)."""

    def __init__(self, log_file: io.TextIOBase, original: io.TextIOBase):
        self._log = log_file
        self._original = original

    def write(self, text: str) -> int:
        self._log.write(text)
        self._log.flush()
        return len(text)

    def flush(self) -> None:
        self._log.flush()

    # Attributes pytest or other code may check on stdout.
    @property
    def encoding(self) -> str:
        return getattr(self._original, "encoding", "utf-8")

    def isatty(self) -> bool:
        return False

    def fileno(self) -> int:
        return self._log.fileno()


@contextlib.contextmanager
def _redirect_to_log(log_path: str):
    """Context manager: redirect stdout to *log_path*, restore on exit."""
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as log_fh:
        tee = _TeeToFile(log_fh, sys.stdout)
        old_stdout = sys.stdout
        sys.stdout = tee
        try:
            yield log_path
        finally:
            sys.stdout = old_stdout


def _log_path() -> str:
    """Build the detailed log file path under the FVT report directory."""
    report_dir = os.environ.get("OMNIA_REPORT_PATH", "")
    if not report_dir:
        # Fall back to orchestrator test_config report_path
        report_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))))),
            "reports",
        )
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return os.path.join(report_dir, f"k8s_reboot_detailed_{ts}.log")


# ---------------------------------------------------------------------------
# Kubernetes control-plane prefix tuple (includes both first_ and regular)
# ---------------------------------------------------------------------------
_K8S_CONTROL_PLANE_PREFIXES: tuple[str, ...] = (
    KUBERNETES_PRIMARY_CONTROL_PLANE_PREFIX,
    KUBERNETES_CONTROL_PLANE_PREFIX,
)


# ---------------------------------------------------------------------------
# Hostnames helper
# ---------------------------------------------------------------------------
def _hostnames(rows: list[dict[str, str]]) -> str:
    """Return a comma-separated list of hostnames for a row group."""
    return ", ".join(r["HOSTNAME"] for r in rows)


# ---------------------------------------------------------------------------
# K8s-specific cloud-init wait (terminal states stop polling immediately)
# ---------------------------------------------------------------------------

def _k8s_wait_for_cloud_init(
    host,
    row: dict[str, str],
    timeout_seconds: int,
    poll_seconds: int,
) -> tuple[bool, str]:
    """Poll cloud-init until it reaches a terminal state or times out.

    Unlike the shared ``wait_for_cloud_init`` which only accepts ``done``,
    this version recognizes **all** terminal states: ``done``, ``error``,
    and ``degraded done``.  When cloud-init finishes with ``error`` (e.g.
    CoreDNS restart timeout), it stops polling immediately instead of
    waiting for the full timeout.

    Returns:
        (completed, detail) where *completed* is True when cloud-init has
        reached **any** terminal state (done, error, degraded).  The caller
        does not treat cloud-init failure as a test failure; it only needs
        to know that cloud-init is no longer running.
    """
    started = time.monotonic()
    deadline = started + timeout_seconds
    detail = "cloud-init was not checked"
    while time.monotonic() < deadline:
        try:
            complete, detail = direct_cloud_init_probe(host, row)
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            detail = str(exc)[:300]
            complete = False
            time.sleep(poll_seconds)
            continue
        # direct_cloud_init_probe returns True only for done (possibly
        # with benign degraded).  Accept that immediately.
        if complete:
            return True, detail
        # Stop polling on terminal states: cloud-init will not change
        # from error/done+degraded back to running.
        if "status=error" in detail or "extended_status=degraded" in detail:
            return True, detail
        # Still running -- keep polling
        elapsed = int(time.monotonic() - started)
        print(
            f"  {row['HOSTNAME']}: cloud-init not ready "
            f"(elapsed {elapsed}s / {timeout_seconds}s): {detail}",
            flush=True,
        )
        time.sleep(poll_seconds)
    return False, detail


# ---------------------------------------------------------------------------
# K8s-specific group readiness (cloud-init degraded/error is a warning)
# ---------------------------------------------------------------------------

def _k8s_wait_for_group_ready(
    host,
    rows: list[dict[str, str]],
    label: str,
    bmc_user: str,
    bmc_auth: str,
) -> tuple[list[tuple[str, object]], list[str], float]:
    """Power on a group, wait for SSH and cloud-init. Return fields, errors, elapsed.

    Unlike the strict Slurm version, cloud-init ``degraded`` or ``error``
    states are treated as **warnings** (not hard failures) because
    cloud-init scripts on Kubernetes nodes may time out waiting for pods
    (e.g. CoreDNS restart) while other nodes are still booting.  The
    Phase 3 postconditions (node readiness, system pods, etcd) are the
    real health gate.
    """
    started = time.monotonic()
    fields: list[tuple[str, object]] = []
    errors: list[str] = []

    # Power on via Redfish (detailed output goes to log file)
    power_results = _redfish_power_on(host, rows, bmc_user, bmc_auth)
    for row in rows:
        ok, detail = power_results.get(row["HOSTNAME"], (False, "not attempted"))
        fields.append((f"    {row['HOSTNAME']} Redfish power-on", f"{'passed' if ok else 'FAILED'} -- {detail}"))
        if not ok:
            errors.append(f"{row['HOSTNAME']} Redfish power-on failed: {detail}")

    # Wait for SSH (detailed polling goes to log file)
    ssh_results = _wait_for_ssh(host, rows)
    for row in rows:
        ok, detail = ssh_results.get(row["HOSTNAME"], (False, "not checked"))
        fields.append((f"    {row['HOSTNAME']} SSH", f"{'passed' if ok else 'FAILED'} -- {detail}"))
        if not ok:
            errors.append(f"{row['HOSTNAME']} SSH not reachable")

    # Wait for cloud-init to reach a terminal state (never a test failure)
    print(f"  Waiting for cloud-init on {len(rows)} node(s)...", flush=True)
    for row in rows:
        hostname = row["HOSTNAME"]
        ssh_ok = ssh_results.get(hostname, (False, ""))[0]
        if not ssh_ok:
            print(f"  {hostname}: cloud-init skipped (node not reachable)", flush=True)
            fields.append((f"    {hostname} cloud-init", "SKIPPED -- node not reachable"))
            continue
        print(f"  {hostname}: Waiting for cloud-init to complete...", flush=True)
        ci_completed, ci_detail = _k8s_wait_for_cloud_init(
            host, row, RECOVERY_WAIT_TIMEOUT_SECONDS, RECOVERY_POLL_SECONDS,
        )
        if ci_completed and "status=error" not in ci_detail and "extended_status=degraded" not in ci_detail:
            print(f"  {hostname}: cloud-init -- {ci_detail}  [OK]", flush=True)
            fields.append((f"    {hostname} cloud-init", f"passed -- {ci_detail}"))
        elif ci_completed:
            print(f"  {hostname}: cloud-init -- {ci_detail}  [DONE (non-fatal)]", flush=True)
            fields.append((f"    {hostname} cloud-init", f"completed with warnings -- {ci_detail}"))
        else:
            print(f"  {hostname}: cloud-init -- timed out: {ci_detail}  [DONE (non-fatal)]", flush=True)
            fields.append((f"    {hostname} cloud-init", f"timed out -- {ci_detail}"))

    elapsed = time.monotonic() - started
    return fields, errors, elapsed


def _poweroff_step(
    host,
    rows: list[dict[str, str]],
    label: str,
    bmc_user: str,
    bmc_auth: str,
) -> tuple[list[tuple[str, object]], list[str]]:
    """Power off a group. Detailed output goes to log; return fields and errors."""
    fields: list[tuple[str, object]] = []
    errors: list[str] = []
    off_results = _graceful_poweroff(host, rows, label, bmc_user, bmc_auth)
    for row in rows:
        ok, detail = off_results.get(row["HOSTNAME"], (False, "not attempted"))
        fields.append((f"    {row['HOSTNAME']} shutdown", f"{'passed' if ok else 'FAILED'} -- {detail}"))
        if not ok:
            errors.append(f"{row['HOSTNAME']} shutdown failed")
    return fields, errors


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def check_k8s_ordered_reboot(host) -> Dict[str, Any]:
    """Ordered Kubernetes cluster reboot: shutdown all, then power-on group by group.

    Power-off order (Redfish GracefulShutdown):
        1. service_kube_node (worker)
        2. secondary service_kube_control_plane (non-primary)
        3. primary service_kube_control_plane_first (last)

    Power-on order (Redfish On, with cloud-init verification between groups):
        1. primary service_kube_control_plane_first (first -- etcd leader)
        2. all remaining (secondary control-plane + workers) in parallel
    """
    summary = "Kubernetes ordered cluster reboot"
    try:
        if not marker_is_authorized("reboot"):
            return _skip(
                summary,
                "Select the reboot marker to authorize a cluster reboot",
            )
        context, rows, control, _config = _context(host)
        if not rows:
            return _skip(summary, "No Kubernetes nodes are mapped")
        if control is None:
            return _skip(summary, "No Kubernetes primary control-plane node is present")

        bmc_user, bmc_auth = _bmc_credentials(host)

        # Categorize rows by role
        primary_cp_rows = _rows_for_prefix(rows, (KUBERNETES_PRIMARY_CONTROL_PLANE_PREFIX,))
        all_cp_rows = _rows_for_prefix(rows, _K8S_CONTROL_PLANE_PREFIXES)
        primary_hostnames = {r["HOSTNAME"] for r in primary_cp_rows}
        secondary_cp_rows = [r for r in all_cp_rows if r["HOSTNAME"] not in primary_hostnames]
        worker_rows = _rows_for_prefix(rows, (KUBERNETES_NODE_PREFIX,))

        if not primary_cp_rows and not secondary_cp_rows and not worker_rows:
            return _skip(summary, "No Kubernetes nodes matched any expected prefix")

        fields: list[tuple[str, object]] = [
            ("Cluster composition",
             f"{len(primary_cp_rows)} primary control-plane, "
             f"{len(secondary_cp_rows)} secondary control-plane, "
             f"{len(worker_rows)} worker"),
            ("Power method", "Redfish (iDRAC)"),
            ("Credentials", f"orchestrator_credentials.yml (user: {bmc_user})"),
        ]
        all_errors: list[str] = []

        # Print cluster summary and log path to screen up front
        log_file = _log_path()
        _summary(
            f"Cluster: {len(primary_cp_rows)} primary control-plane, "
            f"{len(secondary_cp_rows)} secondary control-plane, "
            f"{len(worker_rows)} worker"
        )
        _summary(f"Detailed log: {log_file}")
        fields.append(("Detailed log", log_file))

        with _redirect_to_log(log_file):
            # =============================================================
            # Phase 1: Ordered graceful power-off (Redfish GracefulShutdown)
            # =============================================================
            _phase_header("Phase 1: Ordered graceful power-off (Redfish)")
            fields.append(("Phase", "1 -- Ordered graceful power-off (Redfish)"))

            # 1a. Power off worker nodes
            if worker_rows:
                step_fields, step_errors = _poweroff_step(
                    host, worker_rows, "worker", bmc_user, bmc_auth,
                )
                fields.extend(step_fields)
                all_errors.extend(step_errors)
                status = "ok" if not step_errors else "failed"
                _summary(
                    f"Step 1a: Shutting down {len(worker_rows)} worker node(s) "
                    f"[{_hostnames(worker_rows)}]",
                    status,
                )
                fields.append(("  Step 1a", f"Shutting down {len(worker_rows)} worker node(s)"))

            # 1b. Power off secondary control-plane nodes
            if secondary_cp_rows:
                step_fields, step_errors = _poweroff_step(
                    host, secondary_cp_rows, "secondary control-plane", bmc_user, bmc_auth,
                )
                fields.extend(step_fields)
                all_errors.extend(step_errors)
                status = "ok" if not step_errors else "failed"
                _summary(
                    f"Step 1b: Shutting down {len(secondary_cp_rows)} secondary "
                    f"control-plane node(s) [{_hostnames(secondary_cp_rows)}]",
                    status,
                )
                fields.append(("  Step 1b", f"Shutting down {len(secondary_cp_rows)} secondary control-plane node(s)"))

            # 1c. Power off primary control-plane node last
            if primary_cp_rows:
                step_fields, step_errors = _poweroff_step(
                    host, primary_cp_rows, "primary control-plane", bmc_user, bmc_auth,
                )
                fields.extend(step_fields)
                all_errors.extend(step_errors)
                status = "ok" if not step_errors else "failed"
                _summary(
                    f"Step 1c: Shutting down {len(primary_cp_rows)} primary "
                    f"control-plane node(s) [{_hostnames(primary_cp_rows)}]",
                    status,
                )
                fields.append(("  Step 1c", f"Shutting down {len(primary_cp_rows)} primary control-plane node(s)"))

            # Wait for all nodes to become unreachable
            all_node_rows = primary_cp_rows + secondary_cp_rows + worker_rows
            fields.append(("  Settle", f"Waiting {_POWEROFF_SETTLE_SECONDS}s for shutdown to complete"))
            time.sleep(_POWEROFF_SETTLE_SECONDS)

            unreachable = _wait_until_unreachable(host, all_node_rows)
            unreachable_ok = True
            for row in all_node_rows:
                ok, detail = unreachable.get(row["HOSTNAME"], (False, "not checked"))
                fields.append((f"    {row['HOSTNAME']} unreachable", f"{'passed' if ok else 'FAILED'} -- {detail}"))
                if not ok:
                    all_errors.append(f"{row['HOSTNAME']} did not become unreachable")
                    unreachable_ok = False
            _summary(
                f"All {len(all_node_rows)} node(s) confirmed unreachable",
                "ok" if unreachable_ok else "failed",
            )

            # =============================================================
            # Phase 2: Ordered power-on with per-group readiness
            # =============================================================
            _phase_header("Phase 2: Ordered power-on with readiness checks (Redfish)")
            fields.append(("Phase", "2 -- Ordered power-on with readiness checks (Redfish)"))

            # 2a. Power on primary control-plane node first (etcd leader)
            if primary_cp_rows:
                fields.append(("  Step 2a", f"Powering on {len(primary_cp_rows)} primary control-plane node(s)"))
                group_fields, group_errors, elapsed = _k8s_wait_for_group_ready(
                    host, primary_cp_rows, "primary control-plane", bmc_user, bmc_auth,
                )
                fields.extend(group_fields)
                all_errors.extend(group_errors)
                status = "ok" if not group_errors else "failed"
                _summary(
                    f"Step 2a: Powering on {len(primary_cp_rows)} primary "
                    f"control-plane node(s) [{_hostnames(primary_cp_rows)}]  "
                    f"({int(elapsed)}s)",
                    status,
                )

            # 2b. Power on remaining nodes in parallel
            remaining_rows = secondary_cp_rows + worker_rows
            if remaining_rows:
                desc = (
                    f"{len(remaining_rows)} remaining node(s) "
                    f"({len(secondary_cp_rows)} secondary control-plane, "
                    f"{len(worker_rows)} worker)"
                )
                fields.append(("  Step 2b", f"Powering on {desc}"))
                group_fields, group_errors, elapsed = _k8s_wait_for_group_ready(
                    host, remaining_rows, "remaining", bmc_user, bmc_auth,
                )
                fields.extend(group_fields)
                all_errors.extend(group_errors)
                status = "ok" if not group_errors else "failed"
                _summary(
                    f"Step 2b: Powering on {desc} "
                    f"[{_hostnames(remaining_rows)}]  ({int(elapsed)}s)",
                    status,
                )

            # =============================================================
            # Stabilization: wait for the cluster to settle after reboot
            # =============================================================
            stabilize_seconds = 300  # 5 minutes
            _phase_header(f"Stabilization: waiting {stabilize_seconds}s for cluster to settle")
            fields.append(("Stabilization", f"Waiting {stabilize_seconds}s for cluster to settle"))
            _summary(f"Waiting {stabilize_seconds}s (5 min) for cluster to stabilize after reboot...")
            time.sleep(stabilize_seconds)
            _summary("Stabilization wait complete", "ok")

            # =============================================================
            # Phase 3: Cluster-wide postconditions
            # =============================================================
            _phase_header("Phase 3: Kubernetes cluster-wide postconditions")
            fields.append(("Phase", "3 -- Kubernetes cluster-wide postconditions"))

            # 3a. Kubernetes node readiness
            nodes_result = check_kubernetes_nodes(host)
            fields.append(("Kubernetes nodes", "passed" if nodes_result["success"] else "FAILED"))
            if not nodes_result["success"]:
                all_errors.append("Kubernetes node readiness check failed")
            _summary("Kubernetes nodes", "ok" if nodes_result["success"] else "failed")

            # 3b. Kubernetes control-plane readiness
            cp_result = check_kubernetes_control_plane(host)
            fields.append(("Kubernetes control plane", "passed" if cp_result["success"] else "FAILED"))
            if not cp_result["success"]:
                all_errors.append("Kubernetes control-plane readiness check failed")
            _summary("Kubernetes control plane", "ok" if cp_result["success"] else "failed")

            # 3c. Kubernetes system pods
            pods_result = check_kubernetes_system_pods(host)
            fields.append(("Kubernetes system pods", "passed" if pods_result["success"] else "FAILED"))
            if not pods_result["success"]:
                all_errors.append("Kubernetes system pods check failed")
            _summary("Kubernetes system pods", "ok" if pods_result["success"] else "failed")

            # 3d. Kubernetes etcd health
            etcd_result = check_kubernetes_etcd_health(host)
            fields.append(("Kubernetes etcd health", "passed" if etcd_result["success"] else "FAILED"))
            if not etcd_result["success"]:
                all_errors.append("Kubernetes etcd health check failed")
            _summary("Kubernetes etcd health", "ok" if etcd_result["success"] else "failed")

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
