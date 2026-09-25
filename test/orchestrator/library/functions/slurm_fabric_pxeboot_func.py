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

"""Slurm accelerator, InfiniBand, and UCX verification after PXE."""

import ipaddress
import json
import re

from ..vars.pxeboot_vars import PXEBOOT_COMMANDS, SLURM_COMPUTE_PREFIX
from ._pxeboot_helpers import (
    remote_command,
    runtime_exception,
    runtime_result,
)
from ._workload_helpers import optional_skip as _skip
from ._workload_helpers import slurm_context as _context
from ._workload_helpers import slurm_gpu_rows as _gpu_rows


def _ib_rows(rows):
    return [
        row
        for row in rows
        if str(row.get("IB_NIC_NAME", "")).strip() and str(row.get("IB_IP", "")).strip()
    ]


def _interface_for_ip(payload, expected_ip: str) -> tuple[str, int, str, int]:
    for interface in payload if isinstance(payload, list) else []:
        if not isinstance(interface, dict):
            continue
        for address in interface.get("addr_info", []):
            if not isinstance(address, dict):
                continue
            if str(address.get("local", "")) == expected_ip:
                return (
                    str(interface.get("ifname", "")),
                    int(interface.get("mtu", 0) or 0),
                    str(interface.get("operstate", "")),
                    int(address.get("prefixlen", 0) or 0),
                )
    return "", 0, "", 0


_SLOT_FQDD_RE = re.compile(
    r"^(?:InfiniBand\.PCIe\.Slot\.|InfiniBand\.Slot\.|NIC\.InfiniBand\.)"
    r"([0-9a-fA-F]+)-([1-9][0-9]*)$"
)
_SINGLE_FQDD_RE = re.compile(r"^InfiniBand\.Single-([1-9][0-9]*)$")
_NETDEV_MAP_RE = re.compile(r"^(\S+)\s+port\s+(\d+)\s+==>\s+(\S+)\s+\(([^)]+)\)$")
_UCX_EXECUTABLE_RE = re.compile(r"^UCX_EXECUTABLE\|(.+)$")
_UCX_TRANSPORT_RE = re.compile(r"^\s*#?\s*Transport:\s*(\S+)", re.IGNORECASE)
_UCX_DEVICE_RE = re.compile(r"^\s*#?\s*Device:\s*(\S+)", re.IGNORECASE)
_UCX_IB_TRANSPORT_RE = re.compile(r"^(?:rc|dc|ud|ib)(?:_|$)", re.IGNORECASE)


def _parse_ib_fqdd(fqdd: str) -> tuple[str | None, int]:
    slot_match = _SLOT_FQDD_RE.fullmatch(fqdd)
    if slot_match:
        return slot_match.group(1), int(slot_match.group(2))
    single_match = _SINGLE_FQDD_RE.fullmatch(fqdd)
    if single_match:
        return None, int(single_match.group(1))
    raise ValueError(f"Unsupported IB_NIC_NAME format: {fqdd}")


def _slot_pci_address(output: str, slot: str) -> str:
    designation = ""
    slot_pattern = re.compile(rf"\bSlot\s+{re.escape(slot)}(?:\s|$)", re.IGNORECASE)
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("Designation:"):
            designation = stripped.partition(":")[2].strip()
        elif stripped.startswith("Bus Address:") and slot_pattern.search(designation):
            return stripped.partition(":")[2].strip().lower()
    return ""


def _parse_pci_map(output: str) -> dict[str, str]:
    mapping = {}
    for line in output.splitlines():
        device, separator, pci_address = line.strip().partition("|")
        if separator and device and pci_address:
            mapping[device] = pci_address.lower()
    return mapping


def _parse_netdev_map(output: str) -> dict[tuple[str, int], tuple[str, str]]:
    mapping = {}
    for line in output.splitlines():
        match = _NETDEV_MAP_RE.fullmatch(line.strip())
        if match:
            mapping[(match.group(1), int(match.group(2)))] = (
                match.group(3),
                match.group(4),
            )
    return mapping


def _resolve_ib_interface(fqdd: str, slots: str, pci_map: str, netdev_map: str):
    """Resolve an input FQDD to its runtime RDMA device and Linux netdev."""
    slot, port = _parse_ib_fqdd(fqdd)
    devices = _parse_pci_map(pci_map)
    netdevs = _parse_netdev_map(netdev_map)
    pci_address = ""
    device = ""
    if slot is None:
        candidates = sorted({name for name, _port in netdevs})
        if len(candidates) != 1:
            return {
                "error": (
                    "single-device FQDD is ambiguous; discovered "
                    f"{len(candidates)} RDMA devices"
                )
            }
        device = candidates[0]
        pci_address = devices.get(device, "")
    else:
        pci_address = _slot_pci_address(slots, slot)
        if not pci_address:
            return {"error": f"slot {slot} has no DMI PCI address"}
        exact = [name for name, pci in devices.items() if pci == pci_address]
        if not exact:
            target_bus_device = pci_address.rsplit(".", 1)[0]
            exact = [
                name
                for name, pci in devices.items()
                if pci.rsplit(".", 1)[0] == target_bus_device
            ]
        if len(exact) != 1:
            return {
                "error": (f"PCI {pci_address} resolved to {len(exact)} RDMA devices")
            }
        device = exact[0]
    netdev, link_state = netdevs.get((device, port), ("", ""))
    if not netdev:
        return {"error": f"{device or 'RDMA device'} port {port} has no netdev"}
    return {
        "slot": slot or "single",
        "port": port,
        "pci_address": pci_address or "single-device",
        "device": device,
        "netdev": netdev,
        "link_state": link_state,
        "error": "",
    }


def _runtime_ib_resolution(host, row):
    """Resolve one mapping FQDD against the node's live RDMA inventory."""
    commands = {
        "DMI slot inventory": PXEBOOT_COMMANDS["infiniband_slots"],
        "RDMA PCI inventory": PXEBOOT_COMMANDS["infiniband_pci_map"],
        "RDMA netdev inventory": PXEBOOT_COMMANDS["infiniband_netdev_map"],
    }
    results = {
        label: remote_command(host, row, command) for label, command in commands.items()
    }
    failed = [label for label, result in results.items() if result.rc != 0]
    if failed:
        return {"error": "failed to read " + ", ".join(failed)}
    return _resolve_ib_interface(
        str(row["IB_NIC_NAME"]).strip(),
        results["DMI slot inventory"].stdout,
        results["RDMA PCI inventory"].stdout,
        results["RDMA netdev inventory"].stdout,
    )


def _parse_ucx_inventory(output: str) -> dict[str, object]:
    """Extract stable UCX facts without depending on one UCX release format."""
    executable = ""
    version = ""
    transports = set()
    devices = set()
    for raw_line in output.splitlines():
        line = raw_line.strip()
        executable_match = _UCX_EXECUTABLE_RE.fullmatch(line)
        if executable_match:
            executable = executable_match.group(1).strip()
            continue
        transport_match = _UCX_TRANSPORT_RE.match(raw_line)
        if transport_match:
            transports.add(transport_match.group(1).strip())
            continue
        device_match = _UCX_DEVICE_RE.match(raw_line)
        if device_match:
            devices.add(device_match.group(1).strip())
            continue
        if not version and "version" in line.lower():
            version = line.lstrip("# ").strip()
    ib_transports = sorted(
        transport for transport in transports if _UCX_IB_TRANSPORT_RE.match(transport)
    )
    return {
        "executable": executable,
        "version": version,
        "transports": sorted(transports),
        "ib_transports": ib_transports,
        "devices": sorted(devices),
    }


def _ucx_device_matches(device: str, port: int, discovered: list[str]) -> list[str]:
    """Return UCX devices that represent the expected RDMA device and port."""
    expected_port = f"{device}:{port}"
    return [
        candidate
        for candidate in discovered
        if candidate == device or candidate.startswith(expected_port)
    ]


def _command_failure(result) -> str:
    detail = (result.stderr or result.stdout or f"command rc={result.rc}").strip()
    return re.sub(r"\s+", " ", detail)[:300]


def check_slurm_gpu_inventory(host):
    """Verify GPUs only on mapped nodes where Slurm declares GPU GRES."""
    summary = "Slurm NVIDIA GPU inventory"
    try:
        _context_data, rows, control, _config = _context(host)
        compute_rows = [
            row
            for row in rows
            if row["EXPECTED_FUNCTIONAL_GROUP"].startswith(SLURM_COMPUTE_PREFIX)
        ]
        if not compute_rows:
            return _skip(summary, "No Slurm compute nodes are mapped")
        gpu_rows = _gpu_rows(host, control, compute_rows)
        if not gpu_rows:
            return _skip(
                summary,
                "Slurm reports no GPU GRES on the mapped compute nodes",
            )

        node_results = []
        for row, gres, expected_count in gpu_rows:
            result = remote_command(host, row, PXEBOOT_COMMANDS["gpu"])
            devices = [
                line.strip() for line in result.stdout.splitlines() if line.strip()
            ]
            success = result.rc == 0 and len(devices) == expected_count
            node_results.append(
                (
                    row,
                    gres,
                    expected_count,
                    devices,
                    success,
                    _command_failure(result) if result.rc != 0 else "",
                )
            )

        fields = [("Scheduler GPU nodes", f"{len(gpu_rows)}/{len(compute_rows)}")]
        grouped = {}
        for node_result in node_results:
            grouped.setdefault(node_result[0]["EXPECTED_FUNCTIONAL_GROUP"], []).append(
                node_result
            )
        for group_name, group_nodes in grouped.items():
            valid = sum(1 for result in group_nodes if result[4])
            fields.append(
                ("Functional group", f"[{group_name}] ({valid}/{len(group_nodes)})")
            )
            for row, gres, expected_count, devices, success, diagnostic in group_nodes:
                fields.extend(
                    [
                        (
                            f"  {row['HOSTNAME']}",
                            f"{'✓' if success else '✗'} {row['ADMIN_IP']}",
                        ),
                        ("    Scheduler GRES", f"✓ {gres}"),
                        (
                            "    GPU count",
                            (
                                f"{'✓' if len(devices) == expected_count else '✗'} "
                                f"detected={len(devices)} | expected={expected_count}"
                            ),
                        ),
                    ]
                )
                for index, device in enumerate(devices, start=1):
                    fields.append((f"    GPU {index}", device))
                if diagnostic:
                    fields.append(("    Diagnostic", diagnostic))
        failures = [
            row["HOSTNAME"]
            for row, *_details, success, _error in node_results
            if not success
        ]
        return runtime_result(
            not failures,
            summary,
            fields,
            "GPU inventory validation failed on: " + ", ".join(failures)
            if failures
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_slurm_infiniband_configuration(host):
    """Verify the FQDD-to-RDMA identity chain and operational IB state."""
    summary = "Slurm InfiniBand configuration"
    try:
        _context_data, rows, _control, _config = _context(host)
        ib_rows = _ib_rows(rows)
        if not ib_rows:
            return _skip(summary, "No mapped Slurm node has IB_NIC_NAME and IB_IP")
        node_results = []
        for row in ib_rows:
            expected_ip = str(ipaddress.ip_address(row["IB_IP"].split("/", 1)[0]))
            expected_fqdd = str(row["IB_NIC_NAME"]).strip()
            addresses = remote_command(host, row, PXEBOOT_COMMANDS["ip_addresses"])
            try:
                payload = json.loads(addresses.stdout) if addresses.rc == 0 else []
            except json.JSONDecodeError:
                payload = []
            interface, mtu, state, prefix = _interface_for_ip(payload, expected_ip)
            expected_prefix = (
                int(row["IB_IP"].split("/", 1)[1]) if "/" in row["IB_IP"] else None
            )
            ofed = remote_command(host, row, PXEBOOT_COMMANDS["infiniband_ofed"])
            resolution = _runtime_ib_resolution(host, row)
            resolved_interface = str(resolution.get("netdev", ""))
            identity_ok = not resolution["error"] and interface == resolved_interface
            address_ok = addresses.rc == 0 and bool(interface) and identity_ok
            prefix_ok = expected_prefix is None or prefix == expected_prefix
            state_ok = state.upper() == "UP"
            rdma_link_ok = str(resolution.get("link_state", "")).lower() == "up"
            mtu_ok = mtu >= 2044
            ofed_ok = ofed.rc == 0
            ok = (
                identity_ok
                and address_ok
                and prefix_ok
                and state_ok
                and rdma_link_ok
                and mtu_ok
                and ofed_ok
            )
            node_results.append(
                (
                    row,
                    {
                        "success": ok,
                        "fqdd": expected_fqdd,
                        "resolution": resolution,
                        "identity_ok": identity_ok,
                        "interface": interface or "missing",
                        "address_ok": address_ok,
                        "expected_ip": expected_ip,
                        "prefix": prefix,
                        "prefix_ok": prefix_ok,
                        "state": state or "missing",
                        "state_ok": state_ok,
                        "rdma_link_ok": rdma_link_ok,
                        "mtu": mtu,
                        "mtu_ok": mtu_ok,
                        "ofed_ok": ofed_ok,
                    },
                )
            )
        failed = [
            row["HOSTNAME"] for row, result in node_results if not result["success"]
        ]
        fields = []
        grouped = {}
        for node_result in node_results:
            grouped.setdefault(node_result[0]["EXPECTED_FUNCTIONAL_GROUP"], []).append(
                node_result
            )
        for group_name, group_nodes in grouped.items():
            valid = sum(1 for _row, result in group_nodes if result["success"])
            fields.append(
                ("Functional group", f"[{group_name}] ({valid}/{len(group_nodes)})")
            )
            for row, result in group_nodes:
                resolution = result["resolution"]
                if resolution["error"]:
                    path = resolution["error"]
                else:
                    path = (
                        f"slot {resolution['slot']} -> {resolution['pci_address']} -> "
                        f"{resolution['device']} port {resolution['port']} -> "
                        f"{resolution['netdev']}"
                    )
                fields.extend(
                    [
                        (
                            f"  {row['HOSTNAME']}",
                            f"{'✓' if result['success'] else '✗'} {row['ADMIN_IP']}",
                        ),
                        ("    Input FQDD", result["fqdd"]),
                        (
                            "    Hardware resolution",
                            f"{'✓' if result['identity_ok'] else '✗'} {path}",
                        ),
                        (
                            "    IB address",
                            (
                                f"{'✓' if result['address_ok'] and result['prefix_ok'] else '✗'} "
                                f"{result['expected_ip']}/{result['prefix'] or 'missing'} "
                                f"on {result['interface']}"
                            ),
                        ),
                        (
                            "    Link state",
                            (
                                f"{'✓' if result['state_ok'] and result['rdma_link_ok'] else '✗'} "
                                f"netdev={result['state']} | "
                                f"RDMA={'UP' if result['rdma_link_ok'] else 'DOWN'}"
                            ),
                        ),
                        (
                            "    MTU",
                            f"{'✓' if result['mtu_ok'] else '✗'} {result['mtu'] or 'missing'}",
                        ),
                        (
                            "    OFED",
                            (
                                f"{'✓' if result['ofed_ok'] else '✗'} "
                                f"{'present' if result['ofed_ok'] else 'missing'}"
                            ),
                        ),
                    ]
                )
        return runtime_result(
            not failed,
            summary,
            fields,
            "InfiniBand configuration failed on: " + ", ".join(failed)
            if failed
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_slurm_infiniband_connectivity(host):
    """Verify every mapped Slurm IB endpoint can reach every peer."""
    summary = "Slurm InfiniBand peer connectivity"
    try:
        _runtime, rows, _control, _config = _context(host)
        ib_rows = _ib_rows(rows)
        if len(ib_rows) < 2:
            return _skip(summary, "At least two mapped IB endpoints are required")
        source_results = []
        failures = []
        for source in ib_rows:
            target_results = []
            for target in ib_rows:
                if source["HOSTNAME"] == target["HOSTNAME"]:
                    continue
                target_ip = str(ipaddress.ip_address(target["IB_IP"].split("/", 1)[0]))
                result = remote_command(
                    host,
                    source,
                    PXEBOOT_COMMANDS["infiniband_ping"] % target_ip,
                )
                reachable = result.rc == 0
                target_results.append((target, target_ip, reachable))
                if not reachable:
                    failures.append(f"{source['HOSTNAME']}->{target['HOSTNAME']}")
            source_results.append(
                (
                    source,
                    all(reachable for _target, _ip, reachable in target_results),
                    target_results,
                )
            )
        fields = [("IB pairs checked", len(ib_rows) * (len(ib_rows) - 1))]
        grouped = {}
        for source_result in source_results:
            grouped.setdefault(
                source_result[0]["EXPECTED_FUNCTIONAL_GROUP"], []
            ).append(source_result)
        for group_name, group_sources in grouped.items():
            valid = sum(
                1 for _source, source_ok, _targets in group_sources if source_ok
            )
            fields.append(
                ("Functional group", f"[{group_name}] ({valid}/{len(group_sources)})")
            )
            for source, source_ok, target_results in group_sources:
                source_ip = str(ipaddress.ip_address(source["IB_IP"].split("/", 1)[0]))
                fields.append(
                    (
                        f"  From {source['HOSTNAME']}",
                        f"{'✓' if source_ok else '✗'} {source_ip}",
                    )
                )
                fields.extend(
                    (
                        f"    → {target['HOSTNAME']}",
                        f"{'✓' if reachable else '✗'} {target_ip}",
                    )
                    for target, target_ip, reachable in target_results
                )
        return runtime_result(
            not failures,
            summary,
            fields,
            "Failed IB pairs: " + ", ".join(failures) if failures else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)


def check_slurm_ucx_transport(host):
    """Verify UCX exposes the mapped RDMA device on every compute node."""
    summary = "Slurm UCX InfiniBand transport"
    try:
        context, rows, _control, _config = _context(host)
        if not rows or not context["features"].get("ucx", False):
            return _skip(summary, "UCX is not selected in the active catalog")
        compute_rows = [
            row
            for row in rows
            if row["EXPECTED_FUNCTIONAL_GROUP"].startswith(SLURM_COMPUTE_PREFIX)
        ]
        ucx_rows = _ib_rows(compute_rows)
        if not ucx_rows:
            return _skip(
                summary,
                "No mapped Slurm compute node has IB_NIC_NAME and IB_IP",
            )

        node_results = []
        for row in ucx_rows:
            resolution = _runtime_ib_resolution(host, row)
            probe = remote_command(host, row, PXEBOOT_COMMANDS["ucx_transports"])
            inventory = _parse_ucx_inventory(probe.stdout)
            expected_device = str(resolution.get("device", ""))
            expected_port = int(resolution.get("port", 0) or 0)
            matched_devices = (
                _ucx_device_matches(
                    expected_device,
                    expected_port,
                    list(inventory["devices"]),
                )
                if expected_device and expected_port
                else []
            )
            executable_ok = bool(inventory["executable"])
            transport_ok = bool(inventory["ib_transports"])
            device_ok = bool(matched_devices)
            resolution_ok = not resolution.get("error")
            success = (
                probe.rc == 0
                and resolution_ok
                and executable_ok
                and transport_ok
                and device_ok
            )
            diagnostic = ""
            if probe.rc != 0:
                diagnostic = _command_failure(probe)
            elif not resolution_ok:
                diagnostic = str(resolution["error"])
            elif not transport_ok:
                diagnostic = "no rc, dc, ud, or ib transport was reported"
            elif not device_ok:
                diagnostic = (
                    f"expected {expected_device}:{expected_port}; discovered "
                    + (", ".join(inventory["devices"]) or "no UCX devices")
                )
            node_results.append(
                (row, resolution, inventory, matched_devices, success, diagnostic)
            )

        fields = []
        grouped = {}
        for node_result in node_results:
            grouped.setdefault(node_result[0]["EXPECTED_FUNCTIONAL_GROUP"], []).append(
                node_result
            )
        for group_name, group_nodes in grouped.items():
            valid = sum(1 for result in group_nodes if result[4])
            fields.append(
                ("Functional group", f"[{group_name}] ({valid}/{len(group_nodes)})")
            )
            for row, resolution, inventory, devices, success, diagnostic in group_nodes:
                expected_device = str(resolution.get("device", "missing"))
                expected_port = resolution.get("port", "missing")
                fields.extend(
                    [
                        (
                            f"  {row['HOSTNAME']}",
                            f"{'✓' if success else '✗'} {row['ADMIN_IP']}",
                        ),
                        (
                            "    UCX executable",
                            (
                                f"{'✓' if inventory['executable'] else '✗'} "
                                f"{inventory['executable'] or 'missing'}"
                            ),
                        ),
                        (
                            "    UCX version",
                            str(inventory["version"] or "not reported"),
                        ),
                        (
                            "    Expected RDMA device",
                            (
                                f"{'✓' if not resolution.get('error') else '✗'} "
                                f"{expected_device} port {expected_port}"
                            ),
                        ),
                        (
                            "    UCX IB device",
                            (
                                f"{'✓' if devices else '✗'} "
                                f"{', '.join(devices) or 'not reported'}"
                            ),
                        ),
                        (
                            "    UCX IB transports",
                            (
                                f"{'✓' if inventory['ib_transports'] else '✗'} "
                                f"{', '.join(inventory['ib_transports']) or 'not reported'}"
                            ),
                        ),
                    ]
                )
                if diagnostic:
                    fields.append(("    Diagnostic", diagnostic))
        failed = [result[0]["HOSTNAME"] for result in node_results if not result[4]]
        return runtime_result(
            not failed,
            summary,
            fields,
            "UCX InfiniBand transport validation failed on: " + ", ".join(failed)
            if failed
            else "",
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return runtime_exception(summary, exc)
