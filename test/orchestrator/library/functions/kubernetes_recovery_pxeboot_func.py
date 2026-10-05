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

"""Kubernetes control-plane and local-etcd recovery verification after PXE."""

import ipaddress
import time

from ..vars.pxeboot_vars import (
    PXEBOOT_COMMANDS,
    RECOVERY_POLL_SECONDS,
    RECOVERY_WAIT_TIMEOUT_SECONDS,
)
from ._kubernetes_helpers import resolve_kubernetes_node
from ._pxeboot_helpers import (
    marker_is_authorized,
    remote_command,
    remote_json,
    report_poll_progress,
    runtime_exception,
    runtime_result,
    wait_for_cloud_init,
    wait_for_remote_command,
)
from ._workload_helpers import kubernetes_context as _context
from ._workload_helpers import optional_skip as _skip
from .kubernetes_etcd_pxeboot_func import check_kubernetes_etcd_health
from .kubernetes_runtime_pxeboot_func import check_kubernetes_local_etcd_integrity


def _vip_configuration(context, config) -> tuple[bool, str]:
    cluster_name = str(config.get("cluster_name", ""))
    entries = context["high_availability_config"].get("service_k8s_cluster_ha", [])
    matches = [
        entry
        for entry in entries
        if isinstance(entry, dict) and entry.get("cluster_name") == cluster_name
    ]
    if len(matches) != 1:
        raise ValueError("Kubernetes HA configuration is missing or ambiguous")
    enabled = bool(matches[0].get("enable_k8s_ha", False))
    if not enabled:
        return False, ""
    vip = str(ipaddress.ip_address(str(matches[0].get("virtual_ip_address", ""))))
    return enabled, vip


def _vip_owners(host, rows, vip: str) -> list[str]:
    owners = []
    for row in rows:
        if "control_plane" not in row["EXPECTED_FUNCTIONAL_GROUP"]:
            continue
        try:
            addresses = remote_json(host, row, PXEBOOT_COMMANDS["ip_addresses"])
        except (RuntimeError, ValueError):
            continue
        local = {
            str(info.get("local", ""))
            for interface in addresses
            if isinstance(interface, dict)
            for info in interface.get("addr_info", [])
            if isinstance(info, dict)
        }
        if vip in local:
            owners.append(row["HOSTNAME"])
    return owners


def _wait_for_new_boot(host, row, previous_boot_id: str) -> bool:
    """Wait until the node is reachable with a different kernel boot ID."""
    started = time.monotonic()
    deadline = started + RECOVERY_WAIT_TIMEOUT_SECONDS
    attempt = 0
    while time.monotonic() < deadline:
        attempt += 1
        try:
            current = remote_command(host, row, PXEBOOT_COMMANDS["node_boot_id"])
            current_id = current.stdout.strip()
            if current.rc == 0 and current_id and current_id != previous_boot_id:
                return True
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
    return False


def _cluster_node_name(host, control, row) -> str:
    """Return the node name used by the Kubernetes API."""
    payload = remote_json(host, control, PXEBOOT_COMMANDS["kubernetes_nodes"])
    items = payload.get("items", []) if isinstance(payload, dict) else []
    name, item = resolve_kubernetes_node(
        items,
        row["HOSTNAME"],
        row["ADMIN_IP"],
    )
    if item is None:
        raise ValueError(
            f"Kubernetes does not contain {row['HOSTNAME']}/{row['ADMIN_IP']}"
        )
    return name


def check_kubernetes_control_plane_recovery(host):
    """Reboot the VIP owner and verify failover, cloud-init, and node recovery."""
    summary = "Kubernetes control-plane recovery"
    try:
        if not marker_is_authorized("disruptive"):
            return _skip(
                summary,
                "Select the disruptive marker to authorize a node reboot",
            )
        context, rows, _control, config = _context(host)
        if not rows:
            return _skip(summary, "No Kubernetes nodes are mapped")
        enabled, vip = _vip_configuration(context, config)
        if not enabled:
            return _skip(summary, "Kubernetes HA is disabled")
        control_rows = [
            row for row in rows if "control_plane" in row["EXPECTED_FUNCTIONAL_GROUP"]
        ]
        if len(control_rows) < 2:
            return _skip(summary, "At least two control-plane nodes are required")
        owners = _vip_owners(host, rows, vip)
        if len(owners) != 1:
            raise ValueError(
                f"Expected one VIP owner before reboot, found {len(owners)}"
            )
        owner = next(row for row in control_rows if row["HOSTNAME"] == owners[0])
        watcher = next(
            row for row in control_rows if row["HOSTNAME"] != owner["HOSTNAME"]
        )
        cluster_node_name = _cluster_node_name(host, watcher, owner)
        boot_id = remote_command(host, owner, PXEBOOT_COMMANDS["node_boot_id"])
        previous_boot_id = boot_id.stdout.strip()
        if boot_id.rc != 0 or not previous_boot_id:
            raise RuntimeError("Could not read the control-plane boot identity")
        reboot = remote_command(host, owner, PXEBOOT_COMMANDS["node_reboot"])
        if reboot.rc not in {0, 255}:
            raise RuntimeError("The control-plane reboot request failed")

        failover_owners: list[str] = []
        started = time.monotonic()
        deadline = started + 180
        attempt = 0
        while time.monotonic() < deadline:
            attempt += 1
            failover_owners = _vip_owners(host, rows, vip)
            if len(failover_owners) == 1 and owner["HOSTNAME"] not in failover_owners:
                break
            report_poll_progress(
                "Kubernetes VIP failover",
                attempt,
                started,
                180,
                "owners=" + (", ".join(failover_owners) or "none"),
            )
            time.sleep(RECOVERY_POLL_SECONDS)
        failover_ok = (
            len(failover_owners) == 1 and owner["HOSTNAME"] not in failover_owners
        )
        ssh_ok = _wait_for_new_boot(host, owner, previous_boot_id)
        cloud_init_ok = False
        if ssh_ok:
            cloud_init_ok, _detail = wait_for_cloud_init(
                host,
                owner,
                RECOVERY_WAIT_TIMEOUT_SECONDS,
                RECOVERY_POLL_SECONDS,
            )
        ready_ok = False
        if ssh_ok:
            ready_ok, _detail = wait_for_remote_command(
                host,
                watcher,
                PXEBOOT_COMMANDS["kubernetes_node_ready"] % cluster_node_name,
                RECOVERY_WAIT_TIMEOUT_SECONDS,
                RECOVERY_POLL_SECONDS,
            )
        final_owners = _vip_owners(host, rows, vip)
        final_vip_ok = len(final_owners) == 1
        local_etcd = check_kubernetes_local_etcd_integrity(host)
        local_etcd_ok = local_etcd["success"]
        ok = (
            failover_ok
            and ssh_ok
            and cloud_init_ok
            and ready_ok
            and final_vip_ok
            and local_etcd_ok
        )
        return runtime_result(
            ok,
            summary,
            [
                ("Rebooted node", owner["HOSTNAME"]),
                ("Kubernetes identity", cluster_node_name),
                ("Readiness observer", watcher["HOSTNAME"]),
                ("New boot observed", "passed" if ssh_ok else "failed"),
                ("VIP failover", "passed" if failover_ok else "failed"),
                ("Cloud-init state", "passed" if cloud_init_ok else "failed"),
                ("Kubernetes Ready", "passed" if ready_ok else "failed"),
                (
                    "Local etcd persistence",
                    (
                        "not applicable"
                        if local_etcd.get("skipped")
                        else ("passed" if local_etcd_ok else "failed")
                    ),
                ),
                ("Final VIP owners", ", ".join(final_owners) or "none"),
            ],
            "The rebooted control plane did not complete every recovery postcondition"
            if not ok
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_kubernetes_local_etcd_recovery(host):
    """Reboot one control plane and prove local-etcd identity is preserved."""
    summary = "Kubernetes local-etcd reboot persistence"
    try:
        if not marker_is_authorized("disruptive"):
            return _skip(
                summary,
                "Select the disruptive marker to authorize a node reboot",
            )
        _context_data, rows, control, config = _context(host)
        if not rows or not bool(config.get("etcd_on_local_disk", False)):
            return _skip(summary, "etcd_on_local_disk is disabled")
        before_integrity = check_kubernetes_local_etcd_integrity(host)
        cluster_node_name = _cluster_node_name(host, control, control)
        before = remote_command(
            host,
            control,
            PXEBOOT_COMMANDS["etcd_mount_identity"],
        )
        before_identity = before.stdout.strip()
        if not before_integrity["success"] or before.rc != 0 or not before_identity:
            raise RuntimeError("Local-etcd storage is invalid before reboot")
        boot_id = remote_command(host, control, PXEBOOT_COMMANDS["node_boot_id"])
        previous_boot_id = boot_id.stdout.strip()
        if boot_id.rc != 0 or not previous_boot_id:
            raise RuntimeError("Could not read the local-etcd node boot identity")
        reboot = remote_command(host, control, PXEBOOT_COMMANDS["node_reboot"])
        if reboot.rc not in {0, 255}:
            raise RuntimeError("The local-etcd control-plane reboot request failed")
        ssh_ok = _wait_for_new_boot(host, control, previous_boot_id)
        cloud_ok = False
        if ssh_ok:
            cloud_ok, _detail = wait_for_cloud_init(
                host,
                control,
                RECOVERY_WAIT_TIMEOUT_SECONDS,
                RECOVERY_POLL_SECONDS,
            )
        ready_ok = False
        if ssh_ok:
            ready_ok, _detail = wait_for_remote_command(
                host,
                control,
                PXEBOOT_COMMANDS["kubernetes_node_ready"] % cluster_node_name,
                RECOVERY_WAIT_TIMEOUT_SECONDS,
                RECOVERY_POLL_SECONDS,
            )
        after_integrity = check_kubernetes_local_etcd_integrity(host)
        after = remote_command(
            host,
            control,
            PXEBOOT_COMMANDS["etcd_mount_identity"],
        )
        identity_preserved = (
            after.rc == 0
            and bool(after.stdout.strip())
            and after.stdout.strip() == before_identity
        )
        etcd = check_kubernetes_etcd_health(host)
        ok = (
            ssh_ok
            and cloud_ok
            and ready_ok
            and after_integrity["success"]
            and identity_preserved
            and etcd["success"]
        )
        return runtime_result(
            ok,
            summary,
            [
                ("Rebooted node", control["HOSTNAME"]),
                ("Kubernetes identity", cluster_node_name),
                ("New boot observed", ssh_ok),
                ("Cloud-init completion", cloud_ok),
                ("Kubernetes Ready", ready_ok),
                ("Mount source and UUID preserved", identity_preserved),
                ("Local-etcd integrity", after_integrity["success"]),
                ("etcd endpoint health", etcd["success"]),
            ],
            "Local-etcd identity or cluster health was not preserved across reboot"
            if not ok
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
