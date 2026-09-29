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

"""Slurm post-boot verification derived from supported product behavior."""

import ipaddress
import re

from ..vars.pxeboot_vars import (
    PXEBOOT_COMMANDS,
    SLURM_COMPUTE_PREFIX,
    SLURM_ROLE_SERVICES,
)
from ._pxeboot_helpers import (
    remote_command,
    runtime_exception,
    runtime_result,
)
from ._workload_helpers import optional_skip as _skip
from ._workload_helpers import slurm_context as _context


def _parse_slurm_nodes(output: str) -> dict[str, dict[str, str]]:
    nodes = {}
    for line in output.splitlines():
        attributes = dict(re.findall(r"(?:^|\s)([A-Za-z][A-Za-z0-9]*)=(\S+)", line))
        name = attributes.get("NodeName", "")
        if name:
            nodes[name] = attributes
    return nodes


def check_slurm_membership(host):
    """Verify compute membership, scheduler state, and discovered hardware."""
    summary = "Slurm membership and hardware"
    try:
        _runtime, rows, control, config = _context(host)
        if not rows:
            return _skip(summary, "No Slurm nodes are mapped")
        compute_rows = [
            row
            for row in rows
            if row["EXPECTED_FUNCTIONAL_GROUP"].startswith(SLURM_COMPUTE_PREFIX)
        ]
        if not compute_rows:
            return _skip(summary, "No Slurm compute nodes are mapped")
        result = remote_command(host, control, PXEBOOT_COMMANDS["slurm_nodes"])
        if result.rc != 0:
            raise RuntimeError("scontrol could not read Slurm node state")
        actual = _parse_slurm_nodes(result.stdout)
        node_results = []
        unhealthy_states = {"down", "drain", "fail", "unknown", "future"}
        for row in compute_rows:
            node = actual.get(row["HOSTNAME"])
            if node is None:
                node_results.append((row, False, "not registered", "", ""))
                continue
            state = str(node.get("State", "unknown")).split("+", 1)[0].lower()
            cpus = str(node.get("CPUTot") or node.get("CPUs") or "")
            memory = str(node.get("RealMemory") or "")
            hardware_valid = bool(cpus and memory)
            ok = state not in unhealthy_states and hardware_valid
            node_results.append((row, ok, state, cpus, memory))
        unexpected = sorted(set(actual) - {row["HOSTNAME"] for row in compute_rows})
        failed = [
            row["HOSTNAME"]
            for row, ok, _state, _cpus, _memory in node_results
            if not ok
        ]
        mode = str(config.get("node_discovery_mode", "heterogeneous"))
        fields = [
            ("Discovery mode", mode),
            ("Desired Slurm compute nodes", len(compute_rows)),
            ("Registered Slurm compute nodes", len(actual)),
            ("Unexpected nodes", ", ".join(unexpected) or "none"),
        ]
        grouped = {}
        for result_item in node_results:
            grouped.setdefault(result_item[0]["EXPECTED_FUNCTIONAL_GROUP"], []).append(
                result_item
            )
        for group_name, group_nodes in grouped.items():
            valid = sum(1 for _row, ok, _state, _cpus, _memory in group_nodes if ok)
            fields.append(
                ("Functional group", f"[{group_name}] ({valid}/{len(group_nodes)})")
            )
            for row, ok, state, cpus, memory in group_nodes:
                registered = state != "not registered"
                state_ok = registered and state not in unhealthy_states
                fields.extend(
                    [
                        (
                            f"  {row['HOSTNAME']}",
                            f"{'✓' if ok else '✗'} {row['ADMIN_IP']}",
                        ),
                        (
                            "    State",
                            f"{'✓' if state_ok else '✗'} {state}",
                        ),
                        (
                            "    CPUs",
                            f"{'✓' if cpus else '✗'} {cpus or 'missing'}",
                        ),
                        (
                            "    RealMemory",
                            f"{'✓' if memory else '✗'} {memory or 'missing'}",
                        ),
                    ]
                )
        return runtime_result(
            not failed and not unexpected,
            summary,
            fields,
            "; ".join(
                part
                for part in (
                    "Invalid nodes: " + ", ".join(failed) if failed else "",
                    "Unexpected nodes: " + ", ".join(unexpected) if unexpected else "",
                )
                if part
            ),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def _services_for_role(functional_group: str) -> tuple[str, ...]:
    return next(
        (
            services
            for prefix, services in SLURM_ROLE_SERVICES.items()
            if functional_group.startswith(prefix)
        ),
        (),
    )


def check_slurm_services(host):
    """Verify the exact system services required by every Slurm role."""
    summary = "Slurm role services"
    try:
        context, rows, _control, _config = _context(host)
        if not rows:
            return _skip(summary, "No Slurm nodes are mapped")
        node_results = []
        for row in rows:
            states = {}
            services = list(_services_for_role(row["EXPECTED_FUNCTIONAL_GROUP"]))
            if context["features"].get("openldap", False):
                services.append("sssd")
            for service in services:
                result = remote_command(
                    host,
                    row,
                    PXEBOOT_COMMANDS["node_services"] % service,
                )
                states[service] = result.stdout.strip() if result.rc == 0 else "failed"
            ok = bool(states) and all(state == "active" for state in states.values())
            node_results.append((row, ok, states))

        fields = []
        grouped = {}
        for row, ok, states in node_results:
            grouped.setdefault(row["EXPECTED_FUNCTIONAL_GROUP"], []).append(
                (row, ok, states)
            )
        for group_name, group_nodes in grouped.items():
            valid = sum(1 for _row, ok, _states in group_nodes if ok)
            fields.append(
                ("Functional group", f"[{group_name}] ({valid}/{len(group_nodes)})")
            )
            for row, ok, states in group_nodes:
                fields.append(
                    (
                        f"  {row['HOSTNAME']}",
                        f"{'✓' if ok else '✗'} {row['ADMIN_IP']}",
                    )
                )
                fields.extend(
                    (
                        f"    {service}",
                        f"{'✓' if state == 'active' else '✗'} {state}",
                    )
                    for service, state in states.items()
                )

        failed = [row["HOSTNAME"] for row, ok, _states in node_results if not ok]
        return runtime_result(
            not failed,
            summary,
            fields,
            "Service failures: " + ", ".join(failed) if failed else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_slurm_cross_node_ssh(host):
    """Verify passwordless root SSH for every cross-node role pairing."""
    summary = "Slurm cross-node passwordless SSH"
    try:
        _runtime, rows, _control, _config = _context(host)
        if not rows:
            return _skip(summary, "No Slurm nodes are mapped")
        source_results = []
        failures = []
        checked = 0
        for source in rows:
            target_results = []
            for target in rows:
                if source["HOSTNAME"] == target["HOSTNAME"]:
                    continue
                target_ip = str(ipaddress.ip_address(target["ADMIN_IP"]))
                result = remote_command(
                    host,
                    source,
                    PXEBOOT_COMMANDS["cross_node_ssh"] % target_ip,
                )
                checked += 1
                ok = result.rc == 0
                target_results.append((target, ok))
                if not ok:
                    pair = f"{source['HOSTNAME']}->{target['HOSTNAME']}"
                    failures.append(pair)
            source_results.append(
                (
                    source,
                    all(ok for _target, ok in target_results),
                    target_results,
                )
            )

        fields = [("SSH pairs checked", checked)]
        grouped = {}
        for source_result in source_results:
            grouped.setdefault(
                source_result[0]["EXPECTED_FUNCTIONAL_GROUP"], []
            ).append(source_result)
        for group_name, group_sources in grouped.items():
            valid = sum(1 for _source, ok, _targets in group_sources if ok)
            fields.append(
                (
                    "Functional group",
                    f"[{group_name}] ({valid}/{len(group_sources)})",
                )
            )
            for source, source_ok, target_results in group_sources:
                fields.append(
                    (
                        f"  From {source['HOSTNAME']}",
                        f"{'✓' if source_ok else '✗'} {source['ADMIN_IP']}",
                    )
                )
                fields.extend(
                    (
                        f"    → {target['HOSTNAME']}",
                        f"{'✓' if ok else '✗'} {target['ADMIN_IP']}",
                    )
                    for target, ok in target_results
                )
        return runtime_result(
            not failures,
            summary,
            fields,
            "Failed pairs: " + ", ".join(failures) if failures else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_slurm_scheduler(host):
    """Verify every mapped compute is healthy and in an available partition."""
    summary = "Slurm compute partition readiness"
    try:
        _runtime, rows, control, _config = _context(host)
        if not rows:
            return _skip(summary, "No Slurm nodes are mapped")
        compute_rows = [
            row
            for row in rows
            if row["EXPECTED_FUNCTIONAL_GROUP"].startswith(SLURM_COMPUTE_PREFIX)
        ]
        if not compute_rows:
            return _skip(summary, "No Slurm compute nodes are mapped")
        result = remote_command(host, control, PXEBOOT_COMMANDS["slurm_partitions"])
        if result.rc != 0:
            raise RuntimeError("sinfo could not read Slurm partition state")

        memberships: dict[str, list[tuple[str, str, str]]] = {}
        for line in result.stdout.splitlines():
            parts = [part.strip() for part in line.split("|", 3)]
            if len(parts) != 4 or not parts[0]:
                continue
            node, partition, state, availability = parts
            node = node.split(".", 1)[0]
            memberships.setdefault(node, []).append(
                (partition.rstrip("*"), state, availability.lower())
            )

        unhealthy_states = {
            "down",
            "drain",
            "draining",
            "fail",
            "failing",
            "future",
            "invalid",
            "maint",
            "reboot",
            "unknown",
        }
        node_results = []
        for row in compute_rows:
            records = memberships.get(row["HOSTNAME"], [])
            available = sorted(
                {
                    partition
                    for partition, _state, availability in records
                    if partition and availability == "up"
                }
            )
            states = sorted(
                {
                    state.lower().split("+", 1)[0].rstrip("*~#$@!%^-")
                    for _partition, state, _availability in records
                    if state
                }
            )
            state_ready = bool(states) and not any(
                state in unhealthy_states for state in states
            )
            node_results.append(
                (row, bool(available) and state_ready, records, available, states)
            )

        ready_count = sum(
            1 for _row, ready, _records, _available, _states in node_results if ready
        )
        fields = [
            ("Mapped compute nodes", len(compute_rows)),
            ("Partition-ready compute nodes", f"{ready_count}/{len(compute_rows)}"),
        ]
        for row, ready, records, available, states in node_results:
            if available:
                partition_detail = ", ".join(available)
            elif records:
                partition_detail = "unavailable: " + ", ".join(
                    sorted(
                        {
                            partition or "unnamed"
                            for partition, _state, _availability in records
                        }
                    )
                )
            else:
                partition_detail = "not visible in sinfo"
            state_detail = ", ".join(states) or "missing"
            fields.extend(
                [
                    (
                        f"  {row['HOSTNAME']}",
                        f"{'✓' if ready else '✗'} {row['ADMIN_IP']}",
                    ),
                    (
                        "    Scheduler state",
                        f"{'✓' if state_ready else '✗'} {state_detail}",
                    ),
                    (
                        "    Available partition",
                        f"{'✓' if available else '✗'} {partition_detail}",
                    ),
                ]
            )

        failures = [
            row["HOSTNAME"]
            for row, ready, _records, _available, _states in node_results
            if not ready
        ]
        return runtime_result(
            not failures,
            summary,
            fields,
            "Nodes without healthy scheduler state and an available partition: "
            + ", ".join(failures)
            if failures
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_slurm_pam_policy(host):
    """Verify the complete pam_slurm_adopt integration on compute nodes."""
    summary = "Slurm pam_slurm_adopt integration"
    try:
        context, rows, _control, _config = _context(host)
        if not rows:
            return _skip(summary, "No Slurm nodes are mapped")
        if not context["features"].get("openldap", False):
            return _skip(summary, "OpenLDAP is not enabled")
        compute_rows = [
            row
            for row in rows
            if row["EXPECTED_FUNCTIONAL_GROUP"].startswith(SLURM_COMPUTE_PREFIX)
        ]
        if not compute_rows:
            return _skip(summary, "No Slurm compute nodes are mapped")
        node_results = []
        for row in compute_rows:
            result = remote_command(
                host,
                row,
                PXEBOOT_COMMANDS["pam_adopt_integration"],
            )
            parts = result.stdout.strip().split("|", 2)
            policy_ok = len(parts) > 0 and parts[0] == "configured"
            usepam_ok = len(parts) > 1 and parts[1] == "enabled"
            module_ok = len(parts) > 2 and parts[2] == "available"
            node_results.append(
                (
                    row,
                    result.rc == 0 and policy_ok and usepam_ok and module_ok,
                    policy_ok,
                    usepam_ok,
                    module_ok,
                )
            )
        failed = [row["HOSTNAME"] for row, ok, *_details in node_results if not ok]
        fields = []
        grouped = {}
        for node_result in node_results:
            grouped.setdefault(node_result[0]["EXPECTED_FUNCTIONAL_GROUP"], []).append(
                node_result
            )
        for group_name, group_nodes in grouped.items():
            valid = sum(1 for _row, ok, *_details in group_nodes if ok)
            fields.append(
                ("Functional group", f"[{group_name}] ({valid}/{len(group_nodes)})")
            )
            for row, ok, policy_ok, usepam_ok, module_ok in group_nodes:
                fields.extend(
                    [
                        (
                            f"  {row['HOSTNAME']}",
                            f"{'✓' if ok else '✗'} {row['ADMIN_IP']}",
                        ),
                        (
                            "    SSH daemon PAM",
                            (
                                f"{'✓' if usepam_ok else '✗'} "
                                f"{'enabled' if usepam_ok else 'disabled'}"
                            ),
                        ),
                        (
                            "    pam_slurm_adopt module",
                            (
                                f"{'✓' if module_ok else '✗'} "
                                f"{'available' if module_ok else 'missing'}"
                            ),
                        ),
                        (
                            "    SSH account policy",
                            (
                                f"{'✓' if policy_ok else '✗'} "
                                f"{'configured' if policy_ok else 'missing'}"
                            ),
                        ),
                    ]
                )
        return runtime_result(
            not failed,
            summary,
            fields,
            "pam_slurm_adopt integration incomplete on: " + ", ".join(failed)
            if failed
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_slurm_openmpi_installation(host):
    """Verify the selected OpenMPI runtime on every mapped compute node."""
    summary = "Slurm OpenMPI installation"
    try:
        context, rows, _control, _config = _context(host)
        if not rows or not context["features"].get("openmpi", False):
            return _skip(summary, "OpenMPI is not selected in the active catalog")
        compute_rows = [
            row
            for row in rows
            if row["EXPECTED_FUNCTIONAL_GROUP"].startswith(SLURM_COMPUTE_PREFIX)
        ]
        if not compute_rows:
            return _skip(summary, "No Slurm compute nodes are mapped")

        node_results = []
        for row in compute_rows:
            result = remote_command(host, row, PXEBOOT_COMMANDS["openmpi"])
            output_lines = [
                line.strip() for line in result.stdout.splitlines() if line.strip()
            ]
            executable_line = next(
                (
                    line
                    for line in output_lines
                    if line.startswith("OPENMPI_EXECUTABLE|")
                ),
                "",
            )
            executable = executable_line.partition("|")[2]
            compiler_line = next(
                (line for line in output_lines if line.startswith("OPENMPI_COMPILER|")),
                "",
            )
            compiler = compiler_line.partition("|")[2]
            version = next(
                (
                    line
                    for line in output_lines
                    if line not in {executable_line, compiler_line}
                    and "Open MPI" in line
                ),
                "not reported",
            )
            success = (
                result.rc == 0
                and bool(executable)
                and bool(compiler)
                and version != "not reported"
            )
            diagnostic = re.sub(
                r"\s+",
                " ",
                (result.stderr or result.stdout or f"command rc={result.rc}").strip(),
            )[:300]
            node_results.append(
                (
                    row,
                    success,
                    executable or "missing",
                    compiler or "missing",
                    version,
                    diagnostic,
                )
            )

        fields = []
        grouped = {}
        for node_result in node_results:
            grouped.setdefault(node_result[0]["EXPECTED_FUNCTIONAL_GROUP"], []).append(
                node_result
            )
        for group_name, group_nodes in grouped.items():
            valid = sum(1 for _row, success, *_details in group_nodes if success)
            fields.append(
                ("Functional group", f"[{group_name}] ({valid}/{len(group_nodes)})")
            )
            for row, success, executable, compiler, version, diagnostic in group_nodes:
                fields.extend(
                    [
                        (
                            f"  {row['HOSTNAME']}",
                            f"{'✓' if success else '✗'} {row['ADMIN_IP']}",
                        ),
                        (
                            "    OpenMPI executable",
                            f"{'✓' if executable != 'missing' else '✗'} {executable}",
                        ),
                        (
                            "    OpenMPI compiler",
                            f"{'✓' if compiler != 'missing' else '✗'} {compiler}",
                        ),
                        (
                            "    OpenMPI version",
                            f"{'✓' if version != 'not reported' else '✗'} {version}",
                        ),
                    ]
                )
                if not success:
                    fields.append(("    Diagnostic", diagnostic))
        failures = [
            row["HOSTNAME"] for row, success, *_details in node_results if not success
        ]
        return runtime_result(
            not failures,
            summary,
            fields,
            "OpenMPI installation validation failed on: " + ", ".join(failures)
            if failures
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
