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

from ..vars.pxeboot_vars import (
    PXEBOOT_COMMANDS,
    RECOVERY_POLL_SECONDS,
    RECOVERY_WAIT_TIMEOUT_SECONDS,
    SLURM_COMPILER_PREFIX,
)
from ._pxeboot_helpers import (
    first_row,
    marker_is_authorized,
    remote_command,
    runtime_exception,
    runtime_result,
    wait_for_cloud_init,
    wait_for_remote_command,
)
from ._workload_helpers import ldap_test_username as _ldap_username
from ._workload_helpers import optional_skip as _skip
from ._workload_helpers import slurm_context as _context
from ._workload_helpers import slurm_submission_rows as _submit_rows
from .slurm_pxeboot_func import check_slurm_membership, check_slurm_services


def check_slurm_cluster_recovery(host):
    """Reboot mapped Slurm nodes and verify cloud-init, services, and accounting."""
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
        before = remote_command(host, control, PXEBOOT_COMMANDS["slurm_sbatch"])
        if before.rc != 0 or not before.stdout.strip().isdigit():
            raise RuntimeError("The pre-reboot accounting job did not complete")
        job_id = before.stdout.strip()
        reboot_failures = []
        for row in rows:
            result = remote_command(host, row, PXEBOOT_COMMANDS["node_reboot"])
            if result.rc not in {0, 255}:
                reboot_failures.append(row["HOSTNAME"])
        recovery = {}
        for row in rows:
            ssh_ok, _detail = wait_for_remote_command(
                host,
                row,
                PXEBOOT_COMMANDS["ssh_probe"],
                RECOVERY_WAIT_TIMEOUT_SECONDS,
                RECOVERY_POLL_SECONDS,
            )
            cloud_ok = False
            if ssh_ok:
                cloud_ok, _detail = wait_for_cloud_init(
                    host,
                    row,
                    RECOVERY_WAIT_TIMEOUT_SECONDS,
                    RECOVERY_POLL_SECONDS,
                )
            recovery[row["HOSTNAME"]] = (ssh_ok and cloud_ok, "SSH and cloud-init")
        services = check_slurm_services(host)
        membership = check_slurm_membership(host)
        accounting = remote_command(
            host,
            control,
            PXEBOOT_COMMANDS["slurm_job_accounting"] % job_id,
        )
        accounting_ok = accounting.rc == 0 and accounting.stdout.startswith("COMPLETED")
        ldap_job_ok = True
        if context["features"].get("openldap", False):
            username = _ldap_username()
            submit = _submit_rows(rows)[0]
            ldap_job = remote_command(
                host,
                submit,
                PXEBOOT_COMMANDS["slurm_user_sbatch"] % username,
            )
            ldap_job_ok = ldap_job.rc == 0
        openmpi_ok = True
        if context["features"].get("openmpi", False):
            compiler = first_row(rows, SLURM_COMPILER_PREFIX) or control
            openmpi = remote_command(host, compiler, PXEBOOT_COMMANDS["openmpi_job"])
            openmpi_ok = openmpi.rc == 0 and "Open MPI" in openmpi.stdout
        failed_recovery = [name for name, value in recovery.items() if not value[0]]
        ok = (
            not reboot_failures
            and not failed_recovery
            and services["success"]
            and membership["success"]
            and accounting_ok
            and ldap_job_ok
            and openmpi_ok
        )
        return runtime_result(
            ok,
            summary,
            [
                ("Nodes rebooted", len(rows) - len(reboot_failures)),
                ("Nodes recovered", len(rows) - len(failed_recovery)),
                ("Slurm services", "healthy" if services["success"] else "failed"),
                ("Slurm membership", "healthy" if membership["success"] else "failed"),
                ("Accounting preserved", accounting_ok),
                ("LDAP-user job after reboot", ldap_job_ok),
                ("OpenMPI job after reboot", openmpi_ok),
            ],
            "One or more reboot-recovery postconditions failed" if not ok else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
