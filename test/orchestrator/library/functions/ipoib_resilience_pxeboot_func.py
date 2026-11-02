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

"""ER-ORCH-005 IPoIB resilience: failure modes, NodeAddr reapply, and reboot recovery.

- TC-FVT-016: dual-stack failure classification (``fault_injection``)
- TC-FVT-020: Slurm NodeAddr idempotent reapplication (``reprovision``)
- TC-FVT-025: Slurm controller reboot with IB recovery (``reboot``)
- TC-FVT-026: Slurm compute node reboot with IB recovery (``reboot``)

Every mutation is opt-in and restores the node before the check returns.
"""

import base64
import re
import secrets
import shlex
import time
from pathlib import Path
from typing import Any

from ..vars.ipoib_vars import (
    HEALTH_DEGRADED_IPV6,
    HEALTH_HEALTHY,
    IB_MODE_DUAL_STACK,
    IPOIB_HEALTHY_PEER_STATES,
    IPOIB_HOLD_JOB_SECONDS,
    IPOIB_HOLD_JOB_START_TIMEOUT_SECONDS,
    IPOIB_INTERRUPTED_JOB_STATES,
    IPOIB_MIN_MULTI_REBOOT_NODES,
    IPOIB_MPI_RESULT,
    IPOIB_MPI_UCX_TLS,
    IPOIB_OPENMPI_RECORD,
    IPOIB_RESILIENCE_COMMANDS,
    IPOIB_RESTORE_POLL_SECONDS,
    IPOIB_RESTORE_TIMEOUT_SECONDS,
    IPOIB_UNDISTURBED_JOB_STATES,
    RECOVERY_RECORD_FIELDS,
    SLURM_STATE_FLAG_SUFFIXES,
    STAGE_ADDRESS_STATE,
)
from ..vars.pxeboot_vars import (
    POWERVAULT_DEFAULT_ISCSI_PORT,
    PXEBOOT_COMMANDS,
    RECOVERY_POLL_SECONDS,
    RECOVERY_WAIT_TIMEOUT_SECONDS,
    SLURM_COMPUTE_PREFIX,
)
from ._ipoib_helpers import ib_addr_mode, ib_network_block
from ._ipoib_runtime_helpers import (
    allocation_records,
    classify_live,
    families_for,
    full_mesh,
    hostname,
    ib_interface,
    ib_state,
    interface_addresses,
    interface_names,
    is_compute,
    mesh_failures,
    ping_over_ib,
    verdict_fields,
    wait_for_ib_state,
    wait_for_status,
)
from ._powervault_helpers import (
    get_powervault_entries,
    get_target_nodes,
    verify_bind_mounts,
    verify_multipath_device,
    verify_portal_reachability,
    verify_volume_mounted,
)
from ._pxeboot_helpers import (
    marker_is_authorized,
    remote_command,
    runtime_exception,
    runtime_result,
    wait_for_cloud_init,
    wait_for_remote_command,
)
from ._workload_helpers import optional_skip, slurm_context, slurm_shared_storage
from .ipoib_ipv6_pxeboot_func import (
    _expected_nodeaddr,
    _ipoib_nodes,
    _scontrol_nodeaddr,
)
from .slurm_fabric_pxeboot_func import _probe_ucx_node
from .slurm_recovery_pxeboot_func import _wait_for_new_boot, _wait_for_slurm_state

_ERRORS = (OSError, RuntimeError, TypeError, ValueError, KeyError, TimeoutError)
_FAULT_SKIP = "Select the fault_injection marker to authorize IPoIB fault injection"
_REBOOT_SKIP = "Select the reboot marker to authorize node reboots"


def _result(summary, problems, fields):
    return runtime_result(not problems, summary, fields, "; ".join(problems))


def _quote_all(*values) -> tuple[str, ...]:
    return tuple(shlex.quote(str(value)) for value in values)


# ---------------------------------------------------------------------------
# TC-FVT-016: failure modes
# ---------------------------------------------------------------------------


def _fault_pair(nodes):
    """Return (target, peer): the last IPv6 compute node and one other IPv6 node."""
    candidates = [node for node in nodes if node["ipv6"] and node["prefix6"]]
    computes = [node for node in candidates if is_compute(node)]
    if not computes or len(candidates) < 2:
        return None, None
    target = computes[-1]
    peer = next(node for node in candidates if node is not target)
    return target, peer


def _restore_ipv6(host, target, name, peer, records):
    """Re-add the approved IPv6 and wait until the product reports HEALTHY."""
    row = target["row"]
    remote_command(
        host, row,
        IPOIB_RESILIENCE_COMMANDS["ipv6_addr_add"]
        % _quote_all(target["ipv6"], target["prefix6"], name),
    )
    healthy, verdict = wait_for_status(
        host, target, name, peer, records, HEALTH_HEALTHY,
        IPOIB_RESTORE_TIMEOUT_SECONDS // 2, IPOIB_RESTORE_POLL_SECONDS,
    )
    if not healthy:
        remote_command(
            host, row, IPOIB_RESILIENCE_COMMANDS["nm_device_reapply"] % shlex.quote(name)
        )
        healthy, verdict = wait_for_status(
            host, target, name, peer, records, HEALTH_HEALTHY,
            IPOIB_RESTORE_TIMEOUT_SECONDS // 2, IPOIB_RESTORE_POLL_SECONDS,
        )
    return healthy, verdict


def _fault_setup(host, summary, allowed_modes):
    """Authorize, select the target, and require a HEALTHY product baseline."""
    if not marker_is_authorized("fault_injection"):
        return None, optional_skip(summary, _FAULT_SKIP)
    mode, nodes = _ipoib_nodes(host)
    if mode not in allowed_modes:
        return None, optional_skip(summary, f"ib_addr_mode is {mode}")
    target, peer = _fault_pair(nodes)
    if target is None:
        return None, optional_skip(
            summary, "One IPv6 compute node and one IPv6 peer with IB allocations are required"
        )
    iface, name = ib_interface(host, target)
    if not name:
        return None, runtime_result(
            False, summary, [], f"{hostname(target)} has no interface with its IB address"
        )
    live_records = allocation_records(target, mode)
    baseline = classify_live(host, target, name, peer, live_records)
    fields = [
        ("Target node", f"{hostname(target)} ({target['row']['ADMIN_IP']})"),
        ("Interface", name),
        ("Peer", f"{hostname(peer)} {peer['ipv6']}"),
        ("IB mode", mode),
        *verdict_fields("Baseline", baseline),
    ]
    if baseline["status"] != HEALTH_HEALTHY:
        return None, runtime_result(
            False, summary, fields,
            f"Precondition failed: {hostname(target)} baseline is {baseline['status']}",
        )
    return {
        "mode": mode, "nodes": nodes, "target": target, "peer": peer, "name": name,
        "records": live_records, "ipv4_before": interface_addresses(iface, 4),
        "fields": fields,
    }, None


def _identification_problems(verdict, target, name) -> list[str]:
    problems = []
    if verdict["node_id"] != hostname(target):
        problems.append(f"summary node {verdict['node_id'] or 'missing'}")
    if verdict["interface_id"] != name:
        problems.append(f"summary interface {verdict['interface_id'] or 'missing'}")
    if not verdict["stage"]:
        problems.append("summary stage missing")
    if not verdict["corrective_action"]:
        problems.append("corrective action missing")
    return problems


def _recovery_record_problems(verdict) -> list[str]:
    health = verdict["health"]
    missing = [field for field in RECOVERY_RECORD_FIELDS if health.get(field) in (None, "")]
    return [f"recovery record lacks {', '.join(missing)}"] if missing else []


def check_ipoib_failure_dual_stack(host) -> dict[str, Any]:
    """TC-FVT-016 S1: dual-stack IPv6 failure is DEGRADED_IPV6 with IPv4 preserved."""
    summary = "IPoIB dual-stack IPv6 failure mode"
    try:
        setup, skip = _fault_setup(host, summary, {IB_MODE_DUAL_STACK})
        if skip:
            return skip
        target, peer, name = setup["target"], setup["peer"], setup["name"]
        fields, problems = list(setup["fields"]), []
        try:
            injected = remote_command(
                host, target["row"],
                IPOIB_RESILIENCE_COMMANDS["ipv6_addr_del"]
                % _quote_all(target["ipv6"], target["prefix6"], name),
            )
            if injected.rc != 0:
                return runtime_result(False, summary, fields, "Could not inject IPv6 failure")
            fields.append(("Injected fault", f"removed {target['ipv6']}/{target['prefix6']}"))
            verdict = classify_live(host, target, name, peer, setup["records"])
            iface, _ = ib_interface(host, target)
            ipv4_kept = target["ipv4"] in interface_addresses(iface, 4)
            ipv4_reach = ping_over_ib(host, target, name, peer["ipv4"], 4)
        finally:
            restored, after = _restore_ipv6(host, target, name, peer, setup["records"])
        fields += verdict_fields("Failed state", verdict)
        fields += [
            ("IPv4 address preserved", "yes" if ipv4_kept else "NO"),
            ("IPv4 IB peer reachable", "yes" if ipv4_reach else "NO"),
            ("Restored", f"{'yes' if restored else 'NO'} ({after['status']})"),
        ]
        if verdict["status"] != HEALTH_DEGRADED_IPV6:
            problems.append(f"status {verdict['status']} != {HEALTH_DEGRADED_IPV6}")
        if verdict["stage"] != STAGE_ADDRESS_STATE:
            problems.append(f"stage {verdict['stage']} != {STAGE_ADDRESS_STATE}")
        problems += _identification_problems(verdict, target, name)
        if not ipv4_kept:
            problems.append("IPv4 address lost")
        if not ipv4_reach:
            problems.append("IPv4 connectivity not preserved")
        if not restored:
            problems.append(f"{hostname(target)} did not return to HEALTHY")
        return _result(summary, problems, fields)
    except _ERRORS as exc:
        return runtime_exception(summary, exc)


# ---------------------------------------------------------------------------
# TC-FVT-020: NodeAddr idempotent reapplication
# ---------------------------------------------------------------------------


def _nodeaddr_snapshot(host, control) -> dict[str, Any]:
    conf = remote_command(host, control, IPOIB_RESILIENCE_COMMANDS["slurm_conf"])
    scontrol = remote_command(host, control, PXEBOOT_COMMANDS["slurm_nodes"])
    if conf.rc != 0 or scontrol.rc != 0:
        raise RuntimeError("Could not read slurm.conf or scontrol on the Slurm controller")
    entries: dict[str, list[list[str]]] = {}
    for line in conf.stdout.splitlines():
        match = re.match(r"\s*NodeName=(\S+)", line)
        if match and match.group(1) != "DEFAULT":
            entries.setdefault(match.group(1), []).append(
                re.findall(r"\bNodeAddr=(\S+)", line)
            )
    return {
        "conf": entries,
        "scontrol": _scontrol_nodeaddr(scontrol.stdout),
        "nodes": sorted(entries),
    }


def _snapshot_problems(label, snapshot, names) -> list[str]:
    problems = []
    for name in names:
        lines = snapshot["conf"].get(name, [])
        if len(lines) != 1:
            problems.append(f"{label}: {name} has {len(lines)} NodeName entries")
        elif len(lines[0]) > 1:
            problems.append(f"{label}: {name} has conflicting NodeAddr {lines[0]}")
    return problems


def check_ipoib_nodeaddr_reapply(host) -> dict[str, Any]:
    """TC-FVT-020: rerunning provision leaves Slurm NodeAddr unchanged and unique."""
    summary = "Slurm IPoIB NodeAddr idempotent reapplication"
    try:
        if not marker_is_authorized("reprovision"):
            return optional_skip(
                summary, "Select the reprovision marker to authorize a provision rerun"
            )
        context, rows, control, _config = slurm_context(host)
        compute = [
            row for row in rows if row["EXPECTED_FUNCTIONAL_GROUP"].startswith(SLURM_COMPUTE_PREFIX)
        ]
        if control is None or not compute:
            return optional_skip(summary, "No Slurm compute nodes are mapped")
        mode = ib_addr_mode(ib_network_block(context["network_spec"]))
        names = [row["HOSTNAME"] for row in compute]
        expected = {row["HOSTNAME"]: _expected_nodeaddr(mode, row) for row in compute}
        before = _nodeaddr_snapshot(host, control)
        fields: list[tuple[str, object]] = [("IB mode", mode)]
        precondition = _snapshot_problems("before", before, names) + [
            f"before: {name} NodeAddr {before['scontrol'].get(name, 'missing')} not {label}"
            for name, (allowed, label) in expected.items()
            if before["scontrol"].get(name, "") not in allowed
        ]
        if precondition:
            return runtime_result(
                False, summary, fields,
                "Precondition failed (NodeAddr not previously injected): "
                + "; ".join(precondition),
            )
        from . import run_playbook  # pylint: disable=import-outside-toplevel

        provision = run_playbook(tag="provision")
        fields += [
            ("Provision rerun", f"rc={provision['rc']} in {provision.get('duration', 0):.1f}s"),
        ]
        if not provision["success"]:
            return runtime_result(
                False, summary, fields, f"Provision rerun failed (rc={provision['rc']})"
            )
        after = _nodeaddr_snapshot(host, control)
        problems = _snapshot_problems("after", after, names)
        if after["nodes"] != before["nodes"]:
            problems.append(f"NodeName set changed: {before['nodes']} -> {after['nodes']}")
        for name in names:
            old_conf = before["conf"].get(name, [[]])[0]
            new_conf = after["conf"].get(name, [[]])[0]
            old_live = before["scontrol"].get(name, "")
            new_live = after["scontrol"].get(name, "")
            allowed, label = expected[name]
            ok = old_conf == new_conf and old_live == new_live and new_live in allowed
            fields.append(
                (f"  {name}", f"{'✓' if ok else '✗'} slurm.conf {old_conf or ['unset']} -> "
                 f"{new_conf or ['unset']} | scontrol {old_live} -> {new_live} ({label})")
            )
            if not ok:
                problems.append(f"{name} NodeAddr changed or unexpected")
        return _result(summary, problems, fields)
    except _ERRORS as exc:
        return runtime_exception(summary, exc)


# ---------------------------------------------------------------------------
# Reboot helpers
# ---------------------------------------------------------------------------


def _boot_id(host, row) -> str:
    result = remote_command(host, row, PXEBOOT_COMMANDS["node_boot_id"])
    boot_id = result.stdout.strip()
    if result.rc != 0 or not boot_id:
        raise RuntimeError(f"Could not read boot identity on {row['HOSTNAME']}")
    return boot_id


def _reboot_and_recover(host, nodes, mode) -> dict[str, dict[str, Any]]:
    """Reboot *nodes* together and wait for boot, cloud-init, and IPoIB recovery."""
    outcomes = {}
    boot_ids = {hostname(node): _boot_id(host, node["row"]) for node in nodes}
    for node in nodes:
        accepted = remote_command(host, node["row"], PXEBOOT_COMMANDS["node_reboot"]).rc
        outcomes[hostname(node)] = {"accepted": accepted in {0, 255}}
    for node in nodes:
        outcome = outcomes[hostname(node)]
        outcome["booted"], _ = _wait_for_new_boot(host, node["row"], boot_ids[hostname(node)])
        outcome["cloud"] = (
            wait_for_cloud_init(
                host, node["row"], RECOVERY_WAIT_TIMEOUT_SECONDS, RECOVERY_POLL_SECONDS
            ) if outcome["booted"] else (False, "node did not return")
        )
        outcome["ib"] = (
            wait_for_ib_state(
                host, node, mode, RECOVERY_WAIT_TIMEOUT_SECONDS, RECOVERY_POLL_SECONDS
            ) if outcome["booted"]
            else {"ok": False, "name": "", "problems": ["node did not return"], "details": []}
        )
    return outcomes


def _recovery_fields(node, outcome) -> tuple[list[str], list[tuple[str, object]]]:
    name = hostname(node)
    cloud_ok, cloud_detail = outcome["cloud"]
    problems = []
    if not outcome["accepted"]:
        problems.append(f"{name} reboot not accepted")
    if not outcome["booted"]:
        problems.append(f"{name} did not return")
    if not cloud_ok:
        problems.append(f"{name} cloud-init: {cloud_detail}")
    problems.extend(f"{name} IB: {p}" for p in outcome["ib"]["problems"])
    fields = [
        (f"  {name}", f"{'✓' if not problems else '✗'} {node['row']['ADMIN_IP']}"),
        ("    Reboot / new boot", f"{outcome['accepted']} / {outcome['booted']}"),
        ("    Cloud-init", cloud_detail),
        *[(f"    {label}", value) for label, value in outcome["ib"]["details"]],
    ]
    return problems, fields


def _slurm_idle(host, control, nodes) -> tuple[list[str], list[tuple[str, object]]]:
    problems, fields = [], []
    for node in nodes:
        ok, state = _wait_for_slurm_state(host, control, hostname(node))
        fields.append((f"Slurm state {hostname(node)}", state))
        if not ok:
            problems.append(f"{hostname(node)} Slurm state {state}")
    return problems, fields


def _nodeaddr_problems(host, control, mode, nodes) -> tuple[list[str], list[tuple[str, object]]]:
    out = remote_command(host, control, PXEBOOT_COMMANDS["slurm_nodes"])
    actual = _scontrol_nodeaddr(out.stdout) if out.rc == 0 else {}
    problems, fields = [], []
    for node in nodes:
        allowed, label = _expected_nodeaddr(mode, node["row"])
        value = actual.get(hostname(node), "")
        fields.append((f"NodeAddr {hostname(node)}", f"{value or 'missing'} ({label})"))
        if value not in allowed:
            problems.append(f"{hostname(node)} NodeAddr {value or 'missing'} not {label}")
    return problems, fields


def _ucx_problems(host, context, nodes) -> tuple[list[str], list[tuple[str, object]]]:
    if not context["features"].get("ucx", False):
        return [], [("UCX IB transport", "not applicable (UCX not in catalog)")]
    problems, fields = [], []
    for node in nodes:
        _res, inventory, devices, success, diagnostic = _probe_ucx_node(host, node["row"])
        fields.append(
            (f"UCX {hostname(node)}", f"{', '.join(inventory['ib_transports']) or 'none'} on "
             f"{', '.join(devices) or 'no device'}")
        )
        if not success:
            problems.append(f"{hostname(node)} UCX: {diagnostic}")
    return problems, fields


def _job_state(host, control, job_id) -> str:
    out = remote_command(
        host, control, IPOIB_RESILIENCE_COMMANDS["job_state"] % (job_id, job_id)
    )
    return out.stdout.strip().split()[0].rstrip("+") if out.stdout.strip() else "unknown"


def _mpi_over_ib(host, context, config, control, targets):
    """Run a multi-node MPI job restricted to UCX InfiniBand transports."""
    if not context["features"].get("openmpi", False):
        return None, [("MPI over IB", "not applicable (OpenMPI not in catalog)")]
    discovery = remote_command(host, targets[0]["row"], PXEBOOT_COMMANDS["openmpi"])
    records = {
        match.group(1): match.group(2)
        for line in discovery.stdout.splitlines()
        if (match := IPOIB_OPENMPI_RECORD.fullmatch(line.strip()))
    }
    if discovery.rc != 0 or len(records) != 2:
        return ["OpenMPI toolchain discovery failed"], [("MPI over IB", "toolchain missing")]
    plugins = remote_command(host, control, PXEBOOT_COMMANDS["slurm_mpi_plugins"])
    versions = sorted(set(re.findall(r"\bpmix_v\d+\b", plugins.stdout)),
                      key=lambda value: int(value.rsplit("v", 1)[1]))
    plugin = versions[-1] if versions else "pmix"
    prefix = str(Path(records["OPENMPI_EXECUTABLE"]).parent.parent)
    libraries = f"{prefix}/lib:{prefix}/lib64"
    workspace = (
        f"{slurm_shared_storage(context, config)['mount_point']}"
        f"/.omnia_fvt/ipoib-mpi-{secrets.token_hex(8)}"
    )
    source = Path(__file__).resolve().parents[1] / "vars" / "slurm_mpi_smoke.c"
    encoded = base64.b64encode(source.read_bytes()).decode("ascii")
    binary = f"{workspace}/slurm_mpi_smoke"
    try:
        prepared = remote_command(
            host, control,
            IPOIB_RESILIENCE_COMMANDS["mpi_workspace"]
            % _quote_all(workspace, encoded, f"{workspace}/slurm_mpi_smoke.c"),
        )
        if prepared.rc != 0:
            return ["Could not create the shared MPI workspace"], []
        compile_script = (
            f"export PATH={shlex.quote(prefix + '/bin')}:$PATH; "
            f"export LD_LIBRARY_PATH={shlex.quote(libraries)}:${{LD_LIBRARY_PATH:-}}; "
            f"{shlex.quote(records['OPENMPI_COMPILER'])} "
            f"{shlex.quote(workspace + '/slurm_mpi_smoke.c')} -o {shlex.quote(binary)}"
        )
        compiled = remote_command(
            host, control,
            PXEBOOT_COMMANDS["openmpi_compile"]
            % (hostname(targets[0]), shlex.quote(compile_script)),
        )
        if compiled.rc != 0:
            return ["MPI compilation failed"], [("MPI over IB", "compile failed")]
        export = (
            f"ALL,PATH={prefix}/bin:/usr/bin:/bin,"
            f"LD_LIBRARY_PATH={libraries},PMIX_MCA_gds=hash"
        )
        launch = (
            f"env UCX_TLS={IPOIB_MPI_UCX_TLS} OMPI_MCA_pml=ucx {shlex.quote(binary)}"
        )
        job = remote_command(
            host, control,
            PXEBOOT_COMMANDS["openmpi_job"] % (
                len(targets), len(targets), ",".join(hostname(t) for t in targets),
                plugin, shlex.quote(export), launch,
            ),
        )
        ranks = {
            match.group(3).split(".", 1)[0]
            for line in job.stdout.splitlines()
            if (match := IPOIB_MPI_RESULT.fullmatch(line.strip()))
        }
        expected = {hostname(t) for t in targets}
        ok = job.rc == 0 and ranks == expected
        fields = [
            ("MPI over IB", f"{'passed' if ok else 'FAILED'} | UCX_TLS={IPOIB_MPI_UCX_TLS} | "
             f"pml=ucx | {plugin}"),
            ("MPI ranks on", ", ".join(sorted(ranks)) or "none"),
        ]
        return ([] if ok else [f"MPI over IB failed (rc={job.rc})"]), fields
    finally:
        remote_command(
            host, control,
            IPOIB_RESILIENCE_COMMANDS["mpi_workspace_cleanup"] % _quote_all(workspace, workspace),
        )


def _reboot_setup(host, summary):
    if not marker_is_authorized("reboot"):
        return None, optional_skip(summary, _REBOOT_SKIP)
    context, rows, control, config = slurm_context(host)
    if control is None:
        return None, optional_skip(summary, "No Slurm nodes are mapped")
    mode, nodes = _ipoib_nodes(host)
    families = families_for(mode)
    usable = [node for node in nodes if all(node["ipv6" if f == 6 else "ipv4"] for f in families)]
    return {
        "context": context, "rows": rows, "control": control, "config": config,
        "mode": mode, "families": families, "nodes": usable,
        "computes": [node for node in usable if is_compute(node)],
        "controller": next(
            (node for node in usable if hostname(node) == control["HOSTNAME"]), None
        ),
    }, None


# ---------------------------------------------------------------------------
# TC-FVT-025: controller reboot
# ---------------------------------------------------------------------------


def _powervault_recovery(host, control) -> tuple[list[str], list[tuple[str, object]]]:
    problems, fields = [], []
    for entry in get_powervault_entries(host):
        targets = get_target_nodes(host, entry.get("functional_group_prefix", []))
        if control["HOSTNAME"] not in {target["hostname"] for target in targets}:
            continue
        ip = control["ADMIN_IP"]
        portals = entry.get("ip", []) or []
        portals = [portals] if isinstance(portals, str) else portals
        binds = entry.get("node_mount_point", []) or []
        binds = [binds] if isinstance(binds, str) else binds
        checks = {
            "iSCSI sessions": verify_portal_reachability(
                host, ip, portals, int(entry.get("port") or POWERVAULT_DEFAULT_ISCSI_PORT)
            ),
            "Multipath": verify_multipath_device(host, ip, str(entry.get("volume_id", ""))),
            "Mount": verify_volume_mounted(host, ip, str(entry.get("mount_point", ""))),
            "Bind mounts": verify_bind_mounts(
                host, ip, str(entry.get("mount_point", "")),
                entry.get("node_key", "local_hostname"), binds,
            ),
        }
        for label, result in checks.items():
            fields.append((f"PowerVault {entry.get('name', '')} {label}",
                           "restored" if result["success"] else result["error"]))
            if not result["success"]:
                problems.append(result["error"])
    if not fields:
        fields.append(("PowerVault", "not applicable (no PowerVault on the controller)"))
    return problems, fields


def check_ipoib_controller_reboot_recovery(host) -> dict[str, Any]:
    """TC-FVT-025: controller IB, services, storage, and accounting recover after reboot."""
    summary = "Slurm controller reboot with IPoIB recovery"
    try:
        setup, skip = _reboot_setup(host, summary)
        if skip:
            return skip
        control, ctrl = setup["control"], setup["controller"]
        if ctrl is None:
            return optional_skip(summary, "The Slurm controller has no complete IPoIB allocation")
        before = remote_command(host, control, PXEBOOT_COMMANDS["slurm_sbatch"])
        job_id = before.stdout.strip().split(";")[0]
        if before.rc != 0 or not job_id.isdigit():
            return runtime_result(False, summary, [], "Pre-reboot accounting job failed")
        outcome = _reboot_and_recover(host, [ctrl], setup["mode"])[hostname(ctrl)]
        problems, fields = _recovery_fields(ctrl, outcome)
        fields.insert(0, ("Pre-reboot job", job_id))
        checks = {
            "Services (slurmctld, slurmdbd, mariadb, munge)":
                IPOIB_RESILIENCE_COMMANDS["controller_services"],
            "slurmdbd connected to MariaDB": IPOIB_RESILIENCE_COMMANDS["slurmdbd_database"],
            "Munge authentication": IPOIB_RESILIENCE_COMMANDS["munge_roundtrip"],
        }
        for label, command in checks.items():
            ok, detail = wait_for_remote_command(
                host, control, command, RECOVERY_WAIT_TIMEOUT_SECONDS, RECOVERY_POLL_SECONDS
            )
            fields.append((label, "operational" if ok else detail[:120]))
            if not ok:
                problems.append(f"{label} not operational")
        all_computes = [
            {"row": row} for row in setup["rows"]
            if row["EXPECTED_FUNCTIONAL_GROUP"].startswith(SLURM_COMPUTE_PREFIX)
        ]
        idle_problems, idle_fields = _slurm_idle(host, control, all_computes)
        pv_problems, pv_fields = _powervault_recovery(host, control)
        names = interface_names(host, setup["nodes"])
        pairs = [(c, ctrl) for c in setup["computes"]] + [(ctrl, c) for c in setup["computes"]]
        unreachable = mesh_failures(host, pairs, setup["families"], names)
        accounting = remote_command(
            host, control, PXEBOOT_COMMANDS["slurm_job_accounting"] % job_id
        ).stdout.strip()
        after = remote_command(host, control, PXEBOOT_COMMANDS["slurm_sbatch"])
        fields += idle_fields + pv_fields + [
            ("Controller <-> compute IB mesh",
             f"{len(pairs) * len(setup['families'])} probes | unreachable: "
             f"{', '.join(unreachable) or 'none'}"),
            ("Pre-reboot job accounting", accounting or "missing"),
            ("Post-reboot job", "scheduled and completed" if after.rc == 0 else "FAILED"),
        ]
        problems += idle_problems + pv_problems
        problems += [f"IB unreachable {label}" for label in unreachable]
        if not accounting.startswith("COMPLETED"):
            problems.append(f"pre-reboot job accounting {accounting or 'missing'}")
        if after.rc != 0:
            problems.append("post-reboot job failed")
        return _result(summary, problems, fields)
    except _ERRORS as exc:
        return runtime_exception(summary, exc)


# ---------------------------------------------------------------------------
# TC-FVT-026: compute node reboot
# ---------------------------------------------------------------------------


def _start_hold_job(host, control, node) -> str:
    out = remote_command(
        host, control,
        IPOIB_RESILIENCE_COMMANDS["hold_job"] % (hostname(node), IPOIB_HOLD_JOB_SECONDS),
    )
    job_id = out.stdout.strip().split(";")[0]
    if out.rc != 0 or not job_id.isdigit():
        raise RuntimeError(f"Could not start the hold job on {hostname(node)}")
    deadline = time.monotonic() + IPOIB_HOLD_JOB_START_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if _job_state(host, control, job_id) == "RUNNING":
            return job_id
        time.sleep(IPOIB_RESTORE_POLL_SECONDS)
    remote_command(host, control, IPOIB_RESILIENCE_COMMANDS["cancel_job"] % job_id)
    raise RuntimeError(f"Hold job {job_id} did not start on {hostname(node)}")


def check_ipoib_compute_reboot_recovery(host) -> dict[str, Any]:
    """TC-FVT-026 S1-S4,S6: one compute reboot recovers IB without disturbing peers."""
    summary = "Slurm compute node reboot with IPoIB recovery"
    hold_job, control = "", None
    try:
        setup, skip = _reboot_setup(host, summary)
        if skip:
            return skip
        control, computes, mode = setup["control"], setup["computes"], setup["mode"]
        if len(computes) < 2:
            return optional_skip(summary, "At least two IPoIB compute nodes are required")
        target, others = computes[-1], computes[:-1]
        peers = [node for node in setup["nodes"] if node is not target]
        other_boot = {hostname(node): _boot_id(host, node["row"]) for node in others}
        hold_job = _start_hold_job(host, control, others[0])
        outcome = _reboot_and_recover(host, [target], mode)[hostname(target)]
        problems, fields = _recovery_fields(target, outcome)
        fields.insert(0, ("Rebooted node", hostname(target)))
        fields.insert(1, ("Hold job", f"{hold_job} on {hostname(others[0])}"))
        names = interface_names(host, setup["nodes"])
        pairs = [(target, p) for p in peers] + [(p, target) for p in peers]
        unreachable = mesh_failures(host, pairs, setup["families"], names)
        fields.append(("Rebooted node <-> peers IB mesh",
                       f"{len(pairs) * len(setup['families'])} probes | unreachable: "
                       f"{', '.join(unreachable) or 'none'}"))
        problems += [f"IB unreachable {label}" for label in unreachable]
        for check in (
            _slurm_idle(host, control, [target]),
            _nodeaddr_problems(host, control, mode, [target]),
            _ucx_problems(host, setup["context"], [target]),
        ):
            problems += check[0]
            fields += check[1]
        states = remote_command(host, control, PXEBOOT_COMMANDS["slurm_partitions"]).stdout
        node_states = {
            line.split("|")[0]: line.split("|")[2].lower().rstrip(SLURM_STATE_FLAG_SUFFIXES)
            for line in states.splitlines() if line.count("|") >= 3
        }
        for node in others:
            name = hostname(node)
            same_boot = _boot_id(host, node["row"]) == other_boot[name]
            state = node_states.get(name, "missing")
            ib = ib_state(host, node, mode)
            ok = same_boot and state in IPOIB_HEALTHY_PEER_STATES and ib["ok"]
            ib_detail = "up" if ib["ok"] else "; ".join(ib["problems"])
            fields.append((f"Unaffected {name}",
                           f"{'✓' if ok else '✗'} boot {'unchanged' if same_boot else 'CHANGED'}"
                           f" | Slurm {state} | IB {ib_detail}"))
            if not ok:
                problems.append(f"{name} disturbed by {hostname(target)} reboot")
        other_mesh = mesh_failures(host, full_mesh(others), setup["families"], names)
        problems += [f"IB unreachable {label}" for label in other_mesh]
        job_state = _job_state(host, control, hold_job)
        fields.append(("Hold job state", job_state))
        if (job_state in IPOIB_INTERRUPTED_JOB_STATES
                or job_state not in IPOIB_UNDISTURBED_JOB_STATES):
            problems.append(f"hold job {hold_job} interrupted ({job_state})")
        return _result(summary, problems, fields)
    except _ERRORS as exc:
        return runtime_exception(summary, exc)
    finally:
        if hold_job and control is not None:
            remote_command(host, control, IPOIB_RESILIENCE_COMMANDS["cancel_job"] % hold_job)


def check_ipoib_compute_multi_reboot_recovery(host) -> dict[str, Any]:
    """TC-FVT-026 S5: simultaneous compute reboot restores the full IB mesh and MPI."""
    summary = "Simultaneous compute reboot with IPoIB mesh recovery"
    try:
        setup, skip = _reboot_setup(host, summary)
        if skip:
            return skip
        control, computes = setup["control"], setup["computes"]
        if len(computes) < IPOIB_MIN_MULTI_REBOOT_NODES:
            return optional_skip(
                summary, f"At least {IPOIB_MIN_MULTI_REBOOT_NODES} IPoIB compute nodes are required"
            )
        outcomes = _reboot_and_recover(host, computes, setup["mode"])
        problems, fields = [], [("Rebooted nodes", ", ".join(hostname(n) for n in computes))]
        for node in computes:
            node_problems, node_fields = _recovery_fields(node, outcomes[hostname(node)])
            problems += node_problems
            fields += node_fields
        names = interface_names(host, computes)
        pairs = full_mesh(computes)
        unreachable = mesh_failures(host, pairs, setup["families"], names)
        fields.append(("Full IB mesh", f"{len(pairs)} pairs x {len(setup['families'])} families "
                       f"| unreachable: {', '.join(unreachable) or 'none'}"))
        problems += [f"IB unreachable {label}" for label in unreachable]
        idle_problems, idle_fields = _slurm_idle(host, control, computes)
        mpi_problems, mpi_fields = _mpi_over_ib(
            host, setup["context"], setup["config"], control, computes
        )
        problems += idle_problems + (mpi_problems or [])
        fields += idle_fields + mpi_fields
        return _result(summary, problems, fields)
    except _ERRORS as exc:
        return runtime_exception(summary, exc)
