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

"""TC-FVT-024: PowerVault Ethernet iSCSI and IPoIB coexistence on Slurm controllers."""

import ipaddress
import os
import re
import shlex
from typing import Any

from ..vars.ipoib_vars import (
    IPOIB_CONTROLLER_NFS_PATHS,
    IPOIB_MYSQL_DIR,
    IPOIB_REPROVISION_TIMEOUT_SECONDS,
    IPOIB_RESILIENCE_COMMANDS,
    IPOIB_RESTORE_POLL_SECONDS,
    IPOIB_RESTORE_TIMEOUT_SECONDS,
    IPOIB_SLURMCTLD_STATE_DIR,
    NETWORK_SPEC_FILE,
)
from ..vars.pxeboot_vars import POWERVAULT_DEFAULT_ISCSI_PORT
from ._ipoib_helpers import ib_network_block
from ._ipoib_runtime_helpers import (
    families_for,
    hostname,
    ib_state,
    mesh_failures,
    route_device,
    routes_covering,
    wait_for_ib_state,
)
from ._powervault_helpers import (
    get_powervault_entries,
    get_target_nodes,
    verify_bind_mounts,
    verify_iscsi_discovery,
    verify_multipath_device,
    verify_portal_reachability,
    verify_volume_mounted,
)
from ._prepare_helpers import read_yaml_mapping
from ._pxeboot_helpers import (
    marker_is_authorized,
    remote_command,
    run_remote_with_progress,
    runtime_exception,
)
from ._workload_helpers import optional_skip
from .ipoib_pxeboot_func import _finish, _ipoib_nodes
from .project_func import resolve_target_input_project_path

_ERRORS = (OSError, RuntimeError, TypeError, ValueError, KeyError, TimeoutError)
_ISCSI_IFACE_IP = re.compile(r"^\s*Iface IPaddress:\s*(\S+)", re.MULTILINE)


def _bind_targets(entry: dict[str, Any]) -> list[str]:
    targets = entry.get("node_mount_point", []) or []
    return [targets] if isinstance(targets, str) else list(targets)


def _portals(entry: dict[str, Any]) -> list[str]:
    portals = entry.get("ip", []) or []
    return [portals] if isinstance(portals, str) else [str(p) for p in portals]


def _pv_ib_targets(host, summary):
    """Return (mode, nodes, [(entry, node)]) for PowerVault targets with IPoIB."""
    mode, nodes = _ipoib_nodes(host)
    entries = get_powervault_entries(host)
    if not entries:
        return None, optional_skip(
            summary, "powervault_config is absent or empty in storage_config.yml"
        )
    by_host = {hostname(node): node for node in nodes}
    targets = []
    for entry in entries:
        for target in get_target_nodes(host, entry.get("functional_group_prefix", [])):
            node = by_host.get(target["hostname"])
            if node is not None:
                targets.append((entry, node))
    if not targets:
        return None, optional_skip(
            summary, "No PowerVault target node has an IPoIB allocation in the PXE mapping"
        )
    return (mode, nodes, targets), None


def _peer(nodes, node):
    return next((other for other in nodes if other is not node), None)


def _storage_state(host, entry, node) -> tuple[list[str], list[tuple[str, object]]]:
    """Return PowerVault problems and details for one target node."""
    ip = node["row"]["ADMIN_IP"]
    port = int(entry.get("port") or POWERVAULT_DEFAULT_ISCSI_PORT)
    mount_point = str(entry.get("mount_point", ""))
    binds = _bind_targets(entry)
    portals = verify_portal_reachability(host, ip, _portals(entry), port)
    multipath = verify_multipath_device(host, ip, str(entry.get("volume_id", "")))
    mounted = verify_volume_mounted(host, ip, mount_point)
    bound = (
        verify_bind_mounts(host, ip, mount_point, entry.get("node_key", "local_hostname"), binds)
        if binds
        else {"success": True, "error": ""}
    )
    problems = [
        result["error"]
        for result in (portals, multipath, mounted, bound)
        if not result["success"]
    ]
    sessions = ", ".join(
        f"{item['portal_ip']}={item['session_state']}"
        for item in portals["details"]["results"]
    )
    details = [
        ("iSCSI sessions", sessions or "none"),
        ("Multipath device", multipath["details"].get("mpath_device") or "missing"),
        (f"Mount {mount_point}", "mounted" if mounted["success"] else "NOT mounted"),
        ("Bind mounts", ", ".join(binds) + (" mounted" if bound["success"] else " NOT mounted")
         if binds else "none configured"),
    ]
    return problems, details


def check_ipoib_powervault_coexistence(host) -> dict[str, Any]:
    """TC-FVT-024 S1: IB interface and PowerVault iSCSI storage are both operational."""
    summary = "IPoIB and PowerVault coexistence"
    try:
        selection, skip = _pv_ib_targets(host, summary)
        if skip:
            return skip
        mode, _nodes, targets = selection
        results = []
        for entry, node in targets:
            state = ib_state(host, node, mode)
            problems, storage = _storage_state(host, entry, node)
            problems = [f"IB: {p}" for p in state["problems"]] + problems
            results.append(
                (node, not problems,
                 [("PowerVault", entry.get("name", "unnamed")), *state["details"], *storage])
            )
        return _finish(summary, results, "IPoIB and PowerVault are not both operational on")
    except _ERRORS as exc:
        return runtime_exception(summary, exc)


def check_ipoib_powervault_iscsi_path(host) -> dict[str, Any]:
    """TC-FVT-024 S2: iSCSI traffic routes via Ethernet and never via IPoIB."""
    summary = "PowerVault iSCSI path isolation from IPoIB"
    try:
        selection, skip = _pv_ib_targets(host, summary)
        if skip:
            return skip
        mode, _nodes, targets = selection
        results = []
        for entry, node in targets:
            state = ib_state(host, node, mode)
            name = state["name"]
            problems, details = [], [("IB interface", name or "missing")]
            if not name:
                problems.append("IB interface not found")
            for portal in _portals(entry):
                device = route_device(host, node["row"], portal)
                captured = routes_covering(host, node["row"], name, portal) if name else []
                details.append(
                    (f"Portal {portal}", f"egress {device or 'none'} | IB routes capturing: "
                     f"{', '.join(captured) or 'none'}")
                )
                if not device or device == name:
                    problems.append(f"{portal} egress is {device or 'unresolved'}")
                if captured:
                    problems.append(f"IB routes capture {portal}: {', '.join(captured)}")
            sessions = remote_command(
                host, node["row"], IPOIB_RESILIENCE_COMMANDS["iscsi_session_detail"]
            )
            local = set(_ISCSI_IFACE_IP.findall(sessions.stdout))
            ib_local = {node["ipv4"], node["ipv6"]} - {""}
            details.append(("iSCSI session source", ", ".join(sorted(local)) or "none"))
            if sessions.rc != 0 or not local:
                problems.append("no iSCSI session source address reported")
            elif local & ib_local:
                problems.append("iSCSI sessions are sourced from an IB address")
            details.append(("Result", "Ethernet only" if not problems else "; ".join(problems)))
            results.append((node, not problems, details))
        return _finish(summary, results, "iSCSI traffic is not isolated from IPoIB on")
    except _ERRORS as exc:
        return runtime_exception(summary, exc)


def check_ipoib_powervault_dns_resilience(host) -> dict[str, Any]:
    """TC-FVT-024 S4: IB DNS injection does not break iSCSI target resolution."""
    summary = "PowerVault iSCSI with IPoIB DNS configuration"
    try:
        selection, skip = _pv_ib_targets(host, summary)
        if skip:
            return skip
        _mode, _nodes, targets = selection
        input_dir = resolve_target_input_project_path(host)
        block = ib_network_block(
            read_yaml_mapping(host, os.path.join(input_dir, NETWORK_SPEC_FILE))
        )
        ib_dns = [str(server) for server in block.get("dns") or []]
        results = []
        for entry, node in targets:
            problems = []
            literal = []
            for portal in _portals(entry):
                try:
                    ipaddress.ip_address(portal)
                    literal.append(portal)
                except ValueError:
                    problems.append(f"portal {portal} is a hostname; resolution depends on DNS")
            port = int(entry.get("port") or POWERVAULT_DEFAULT_ISCSI_PORT)
            ip = node["row"]["ADMIN_IP"]
            discovery = verify_iscsi_discovery(host, ip, literal, port)
            portals = verify_portal_reachability(host, ip, literal, port)
            problems.extend(r["error"] for r in (discovery, portals) if not r["success"])
            attributes = remote_command(
                host, node["row"], IPOIB_RESILIENCE_COMMANDS["resolv_attributes"]
            )
            flags = attributes.stdout.split()[0] if attributes.stdout.split() else ""
            immutable = "i" in flags
            if ib_dns and not immutable:
                problems.append("resolv.conf immutable protection was not restored")
            results.append(
                (node, not problems, [
                    ("IB DNS servers", ", ".join(ib_dns) or "none configured"),
                    ("Portals by IP", ", ".join(literal) or "none"),
                    ("Target discovery", discovery["details"]["discovered_iqn"] or "FAILED"),
                    ("Sessions", "LOGGED_IN" if portals["success"] else portals["error"]),
                    ("resolv.conf immutable", "yes" if immutable else "no"),
                ])
            )
        return _finish(summary, results, "iSCSI resolution is affected by IB DNS on")
    except _ERRORS as exc:
        return runtime_exception(summary, exc)


def _nfs_problems(host, node, ib_name):
    problems, details = [], []
    for path in IPOIB_CONTROLLER_NFS_PATHS:
        out = remote_command(
            host, node["row"],
            IPOIB_RESILIENCE_COMMANDS["findmnt_mountpoint"] % shlex.quote(path),
        )
        parts = out.stdout.split()
        if out.rc != 0 or len(parts) < 4:
            problems.append(f"{path} is not a mount point")
            details.append((f"NFS {path}", "not mounted"))
            continue
        _target, source, fstype, options = parts[:4]
        server = source.rsplit(":", 1)[0].strip("[]")
        device = route_device(host, node["row"], server)
        accessible = remote_command(
            host, node["row"],
            IPOIB_RESILIENCE_COMMANDS["path_accessible"] % (shlex.quote(path), shlex.quote(path)),
        ).rc == 0
        tcp = "proto=tcp" in options.split(",")
        if not fstype.startswith("nfs"):
            problems.append(f"{path} fstype {fstype}")
        if not tcp:
            problems.append(f"{path} is not using TCP transport")
        if not device or device == ib_name:
            problems.append(f"{path} NFS server {server} egress {device or 'unresolved'}")
        if not accessible:
            problems.append(f"{path} not accessible")
        details.append(
            (f"NFS {path}", f"{fstype} {'tcp' if tcp else 'non-tcp'} via {device or '?'} | "
             f"{'accessible' if accessible else 'NOT accessible'}")
        )
    return problems, details


def check_ipoib_powervault_nfs_coexistence(host) -> dict[str, Any]:
    """TC-FVT-024 S5: NFS, PowerVault, and IPoIB work together on the controller."""
    summary = "Controller NFS, PowerVault, and IPoIB coexistence"
    try:
        selection, skip = _pv_ib_targets(host, summary)
        if skip:
            return skip
        mode, nodes, targets = selection
        results = []
        for entry, node in targets:
            state = ib_state(host, node, mode)
            problems = [f"IB: {p}" for p in state["problems"]]
            nfs_problems, details = _nfs_problems(host, node, state["name"])
            problems.extend(nfs_problems)
            peer = _peer(nodes, node)
            if peer is not None:
                unreachable = mesh_failures(
                    host, [(node, peer)], families_for(mode), {hostname(node): state["name"]}
                )
                problems.extend(f"IB peer unreachable: {label}" for label in unreachable)
                details.append(("IB fabric peer", f"{hostname(peer)} "
                                f"{'reachable' if not unreachable else 'UNREACHABLE'}"))
            pv_paths = [str(entry.get("mount_point", "")), *_bind_targets(entry)]
            for path in pv_paths:
                ok = remote_command(
                    host, node["row"],
                    IPOIB_RESILIENCE_COMMANDS["path_accessible"]
                    % (shlex.quote(path), shlex.quote(path)),
                ).rc == 0
                if not ok:
                    problems.append(f"PowerVault path {path} not accessible")
            details.append(("PowerVault paths", ", ".join(pv_paths)))
            mounts = remote_command(host, node["row"], IPOIB_RESILIENCE_COMMANDS["findmnt_all"])
            counts: dict[str, int] = {}
            for line in mounts.stdout.splitlines():
                target = line.split(" ", 1)[0]
                counts[target] = counts.get(target, 0) + 1
            stacked = [
                path for path in (*IPOIB_CONTROLLER_NFS_PATHS, *pv_paths) if counts.get(path, 0) > 1
            ]
            if stacked:
                problems.append("stacked mounts (namespace conflict): " + ", ".join(stacked))
            details.append(("Mount conflicts", ", ".join(stacked) or "none"))
            details.append(("Result", "coexisting" if not problems else "; ".join(problems)))
            results.append((node, not problems, details))
        return _finish(summary, results, "NFS, PowerVault, and IPoIB do not coexist on")
    except _ERRORS as exc:
        return runtime_exception(summary, exc)


def check_ipoib_powervault_ib_reprovision(host) -> dict[str, Any]:
    """TC-FVT-024 S3: PowerVault binds and Slurm state survive IB re-provisioning.

    Re-runs the product's cloud-init IB script (configure-ib-network.sh) on the
    PowerVault target, which deletes, recreates, and re-activates the IPoIB
    NetworkManager profile exactly as idempotent re-provisioning does.
    """
    summary = "PowerVault persistence across IPoIB re-provisioning"
    try:
        if not marker_is_authorized("fault_injection"):
            return optional_skip(
                summary, "Select the fault_injection marker to authorize IB re-provisioning"
            )
        selection, skip = _pv_ib_targets(host, summary)
        if skip:
            return skip
        mode, nodes, targets = selection
        results = []
        for entry, node in targets:
            row = node["row"]
            before = ib_state(host, node, mode)
            pre_problems, _ = _storage_state(host, entry, node)
            if not before["ok"] or pre_problems:
                results.append((node, False, [
                    ("Precondition", "; ".join(before["problems"] + pre_problems)),
                ]))
                continue
            present = remote_command(
                host, row, IPOIB_RESILIENCE_COMMANDS["ib_reprovision_present"]
            )
            if present.rc != 0:
                results.append((node, False, [
                    ("Re-provision", "configure-ib-network.sh is not installed on the node"),
                ]))
                continue
            run = run_remote_with_progress(
                host, row, IPOIB_RESILIENCE_COMMANDS["ib_reprovision"],
                f"{hostname(node)} IB re-provision",
                IPOIB_REPROVISION_TIMEOUT_SECONDS, IPOIB_RESTORE_POLL_SECONDS,
            )
            after = wait_for_ib_state(
                host, node, mode, IPOIB_RESTORE_TIMEOUT_SECONDS, IPOIB_RESTORE_POLL_SECONDS
            )
            peer = _peer(nodes, node)
            unreachable = (
                mesh_failures(host, [(node, peer)], families_for(mode),
                              {hostname(node): after["name"]})
                if peer is not None else []
            )
            storage_problems, storage = _storage_state(host, entry, node)
            state_rw = remote_command(
                host, row,
                IPOIB_RESILIENCE_COMMANDS["state_dir_rw"] % shlex.quote(IPOIB_SLURMCTLD_STATE_DIR),
            ).rc == 0
            mysql_ok = remote_command(
                host, row,
                IPOIB_RESILIENCE_COMMANDS["path_accessible"]
                % (shlex.quote(IPOIB_MYSQL_DIR), shlex.quote(IPOIB_MYSQL_DIR)),
            ).rc == 0
            slurmctld = remote_command(
                host, row, IPOIB_RESILIENCE_COMMANDS["slurmctld_active"]
            ).stdout.strip()
            problems = []
            if run.rc != 0:
                problems.append(f"configure-ib-network.sh rc={run.rc}")
            problems.extend(f"IB: {p}" for p in after["problems"])
            problems.extend(f"IB peer unreachable: {label}" for label in unreachable)
            problems.extend(storage_problems)
            if not state_rw:
                problems.append(f"{IPOIB_SLURMCTLD_STATE_DIR} not read/write")
            if not mysql_ok:
                problems.append(f"{IPOIB_MYSQL_DIR} not accessible")
            if slurmctld != "active":
                problems.append(f"slurmctld {slurmctld or 'unknown'}")
            results.append((node, not problems, [
                ("Re-provision", f"configure-ib-network.sh rc={run.rc}"),
                *after["details"],
                ("IB fabric peer", "reachable" if not unreachable else ", ".join(unreachable)),
                *storage,
                (IPOIB_SLURMCTLD_STATE_DIR, "read/write" if state_rw else "FAILED"),
                (IPOIB_MYSQL_DIR, "accessible" if mysql_ok else "FAILED"),
                ("slurmctld", slurmctld or "unknown"),
            ]))
        return _finish(summary, results, "PowerVault or IB not intact after re-provisioning on")
    except _ERRORS as exc:
        return runtime_exception(summary, exc)
