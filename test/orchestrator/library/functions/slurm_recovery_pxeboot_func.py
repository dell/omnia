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

"""Slurm reboot recovery and post-reboot state verification."""

import re
import time

from ..vars.pxeboot_vars import (
    PXEBOOT_COMMANDS,
    RECOVERY_POLL_SECONDS,
    RECOVERY_WAIT_TIMEOUT_SECONDS,
    SLURM_COMPILER_PREFIX,
    SLURM_COMPUTE_PREFIX,
)
from ._pxeboot_helpers import (
    first_row,
    marker_is_authorized,
    remote_command,
    report_poll_progress,
    runtime_exception,
    runtime_result,
    wait_for_cloud_init,
)
from ._workload_helpers import ldap_test_username as _ldap_username
from ._workload_helpers import optional_skip as _skip
from ._workload_helpers import slurm_context as _context
from ._workload_helpers import slurm_submission_rows as _submit_rows
from .slurm_pxeboot_func import check_slurm_membership, check_slurm_services


def _wait_for_new_boot(host, row, previous_boot_id):
    """Wait until *row* is reachable with a different kernel boot ID."""
    started = time.monotonic()
    deadline = started + RECOVERY_WAIT_TIMEOUT_SECONDS
    attempt = 0
    while time.monotonic() < deadline:
        attempt += 1
        try:
            result = remote_command(host, row, PXEBOOT_COMMANDS["node_boot_id"])
            current_id = result.stdout.strip()
            if result.rc == 0 and current_id and current_id != previous_boot_id:
                return True, current_id
            detail = "waiting for a new kernel boot identity"
        except (OSError, RuntimeError, ValueError) as exc:
            detail = f"node not reachable: {str(exc)[:100]}"
        report_poll_progress(
            f"{row['HOSTNAME']} reboot",
            attempt,
            started,
            RECOVERY_WAIT_TIMEOUT_SECONDS,
            detail,
        )
        time.sleep(RECOVERY_POLL_SECONDS)
    return False, ""


def _wait_for_slurm_state(host, control, node_name, desired="idle"):
    """Poll Slurm until *node_name* reaches *desired* state or times out."""
    started = time.monotonic()
    deadline = started + RECOVERY_WAIT_TIMEOUT_SECONDS
    state = "unknown"
    attempt = 0
    while time.monotonic() < deadline:
        attempt += 1
        result = remote_command(
            host,
            control,
            PXEBOOT_COMMANDS["slurm_node_state"] % node_name,
        )
        state = result.stdout.strip().lower().split("+", 1)[0].rstrip("*~#$@!%^")
        if result.rc == 0 and state == desired:
            return True, state
        report_poll_progress(
            f"{node_name} Slurm state",
            attempt,
            started,
            RECOVERY_WAIT_TIMEOUT_SECONDS,
            f"state={state}",
        )
        time.sleep(RECOVERY_POLL_SECONDS)
    return False, state


def check_slurm_cluster_recovery(host):
    """Reboot mapped Slurm nodes and verify boot, cloud-init, services, and accounting.

    Recovery verification proceeds in phases, each reported per node:

    1. **Pre-reboot baseline** — capture boot IDs and submit an accounting job.
    2. **Reboot** — issue ``systemctl reboot`` on every mapped node.
    3. **Boot verification** — wait for a new kernel boot ID on each node.
    4. **Cloud-init completion** — poll cloud-init until ``done``.
    5. **Slurm state recovery** — poll ``sinfo`` until every compute node is idle.
    6. **Cluster-wide postconditions** — services, membership, accounting,
       optional LDAP job, optional OpenMPI discovery.
    """
    summary = "Slurm cluster reboot recovery"
    try:
        if not marker_is_authorized("disruptive"):
            return _skip(
                summary,
                "Select the disruptive marker to authorize a cluster reboot",
            )
        context, rows, control, _config = _context(host)
        if not rows:
            return _skip(summary, "No Slurm nodes are mapped")

        # --- Phase 1: pre-reboot baseline ---
        boot_ids = {}
        for row in rows:
            result = remote_command(host, row, PXEBOOT_COMMANDS["node_boot_id"])
            boot_id = result.stdout.strip()
            if result.rc != 0 or not boot_id:
                raise RuntimeError(
                    f"Could not read boot identity on {row['HOSTNAME']}"
                )
            boot_ids[row["HOSTNAME"]] = boot_id

        before = remote_command(host, control, PXEBOOT_COMMANDS["slurm_sbatch"])
        if before.rc != 0 or not before.stdout.strip().split(";")[0].isdigit():
            raise RuntimeError(
                "Pre-reboot accounting job failed: "
                + (before.stderr or before.stdout or f"rc={before.rc}").strip()[:200]
            )
        job_id = before.stdout.strip().split(";")[0]

        # --- Phase 2: reboot ---
        reboot_results = {}
        for row in rows:
            result = remote_command(host, row, PXEBOOT_COMMANDS["node_reboot"])
            reboot_results[row["HOSTNAME"]] = result.rc in {0, 255}

        # --- Phase 3: boot verification (per-node boot ID change) ---
        boot_results = {}
        for row in rows:
            new_boot, _new_id = _wait_for_new_boot(
                host, row, boot_ids[row["HOSTNAME"]]
            )
            boot_results[row["HOSTNAME"]] = new_boot

        # --- Phase 4: cloud-init completion ---
        cloud_results = {}
        for row in rows:
            if not boot_results[row["HOSTNAME"]]:
                cloud_results[row["HOSTNAME"]] = (False, "node did not return")
                continue
            cloud_ok, cloud_detail = wait_for_cloud_init(
                host, row, RECOVERY_WAIT_TIMEOUT_SECONDS, RECOVERY_POLL_SECONDS,
            )
            cloud_results[row["HOSTNAME"]] = (cloud_ok, cloud_detail)

        # --- Phase 5: Slurm node state recovery ---
        slurm_state_results = {}
        compute_rows = [
            row
            for row in rows
            if row["EXPECTED_FUNCTIONAL_GROUP"].startswith(SLURM_COMPUTE_PREFIX)
        ]
        for row in compute_rows:
            if not boot_results[row["HOSTNAME"]]:
                slurm_state_results[row["HOSTNAME"]] = (False, "not checked")
                continue
            state_ok, state = _wait_for_slurm_state(
                host, control, row["HOSTNAME"]
            )
            slurm_state_results[row["HOSTNAME"]] = (state_ok, state)

        # --- Phase 6: cluster-wide postconditions ---
        services = check_slurm_services(host)
        membership = check_slurm_membership(host)

        accounting = remote_command(
            host, control, PXEBOOT_COMMANDS["slurm_job_accounting"] % job_id,
        )
        accounting_state = accounting.stdout.strip() if accounting.rc == 0 else "error"
        accounting_ok = accounting_state.startswith("COMPLETED")

        ldap_ok = True
        ldap_detail = "not applicable"
        if context["features"].get("openldap", False):
            username = _ldap_username()
            submit_rows = _submit_rows(rows)
            if submit_rows:
                ldap_job = remote_command(
                    host, submit_rows[0],
                    PXEBOOT_COMMANDS["slurm_user_sbatch"] % username,
                )
                ldap_ok = ldap_job.rc == 0
                ldap_detail = (
                    "passed" if ldap_ok
                    else re.sub(
                        r"\s+", " ",
                        (ldap_job.stderr or ldap_job.stdout or "unknown").strip(),
                    )[:200]
                )

        openmpi_ok = True
        openmpi_detail = "not applicable"
        if context["features"].get("openmpi", False):
            compiler = first_row(rows, SLURM_COMPILER_PREFIX) or control
            openmpi = remote_command(
                host, compiler, PXEBOOT_COMMANDS["openmpi"],
            )
            openmpi_ok = openmpi.rc == 0 and any(
                "Open MPI" in line for line in openmpi.stdout.splitlines()
            )
            openmpi_detail = (
                "passed" if openmpi_ok
                else re.sub(
                    r"\s+", " ",
                    (openmpi.stderr or openmpi.stdout or "unknown").strip(),
                )[:200]
            )

        # --- Build result fields (per-node detail) ---
        fields = []
        for row in rows:
            name = row["HOSTNAME"]
            rebooted = reboot_results.get(name, False)
            booted = boot_results.get(name, False)
            cloud_ok, cloud_detail = cloud_results.get(name, (False, "not checked"))
            fields.append((
                f"  {name}",
                f"{'passed' if rebooted and booted and cloud_ok else 'FAILED'} "
                f"| {row['ADMIN_IP']}",
            ))
            fields.append((
                "    Reboot accepted",
                "passed" if rebooted else "FAILED",
            ))
            fields.append((
                "    New boot observed",
                "passed" if booted else "FAILED — node did not return",
            ))
            fields.append((
                "    Cloud-init",
                f"{'passed' if cloud_ok else 'FAILED'} — {cloud_detail}",
            ))
            if name in slurm_state_results:
                s_ok, s_state = slurm_state_results[name]
                fields.append((
                    "    Slurm state",
                    f"{'passed' if s_ok else 'FAILED'} — {s_state}",
                ))

        fields.extend([
            ("Slurm services", "passed" if services["success"] else "FAILED"),
            ("Slurm membership", "passed" if membership["success"] else "FAILED"),
            (
                "Accounting preserved",
                f"{'passed' if accounting_ok else 'FAILED'} — {accounting_state}",
            ),
            ("LDAP-user job", ldap_detail),
            ("OpenMPI discovery", openmpi_detail),
        ])

        # --- Aggregate success ---
        reboot_failures = [n for n, v in reboot_results.items() if not v]
        boot_failures = [n for n, v in boot_results.items() if not v]
        cloud_failures = [n for n, (v, _d) in cloud_results.items() if not v]
        state_failures = [n for n, (v, _s) in slurm_state_results.items() if not v]

        ok = (
            not reboot_failures
            and not boot_failures
            and not cloud_failures
            and not state_failures
            and services["success"]
            and membership["success"]
            and accounting_ok
            and ldap_ok
            and openmpi_ok
        )
        error_parts = []
        if reboot_failures:
            error_parts.append(f"reboot failed: {', '.join(reboot_failures)}")
        if boot_failures:
            error_parts.append(f"did not return: {', '.join(boot_failures)}")
        if cloud_failures:
            error_parts.append(f"cloud-init failed: {', '.join(cloud_failures)}")
        if state_failures:
            error_parts.append(f"Slurm state not idle: {', '.join(state_failures)}")
        if not services["success"]:
            error_parts.append("Slurm services unhealthy")
        if not membership["success"]:
            error_parts.append("Slurm membership invalid")
        if not accounting_ok:
            error_parts.append(f"accounting state={accounting_state}")
        if not ldap_ok:
            error_parts.append("LDAP-user job failed")
        if not openmpi_ok:
            error_parts.append("OpenMPI discovery failed")

        return runtime_result(
            ok,
            summary,
            fields,
            "; ".join(error_parts) if error_parts else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
