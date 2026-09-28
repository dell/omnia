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
"""NetworkManager renderer for IPoIB IPv6 configuration (ER-ORCH-005).

Generates nmcli commands for dual-stack, IPv6-only, and IPv4-only IPoIB
interfaces.  Each interface produces a single managed NM profile delivered
through cloud-init user-data (write_files + runcmd).

Design decisions (from HLD):
- nmcli is the canonical NM configuration tool (not ip/ifcfg)
- One NM profile per IPoIB interface
- Privacy extensions disabled on every IPoIB interface
- No IPoIB gateway, default route, RA, or static route
- Cloud-init delivery via BSS user-data
"""

from __future__ import annotations

from logging import Logger
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROFILE_PREFIX = "omnia-ipoib"
MANAGED_MARKER = "# Managed by Omnia Orchestrator — do not edit"
HOSTS_BEGIN_MARKER = "# BEGIN Omnia IPoIB managed block"
HOSTS_END_MARKER = "# END Omnia IPoIB managed block"


# ---------------------------------------------------------------------------
# Routed input rejection (FR-3, AC-002)
# ---------------------------------------------------------------------------

_ROUTED_KEYS = frozenset({
    "gateway", "gateway4", "gateway6",
    "ipv4_gateway", "ipv6_gateway",
    "static_routes", "routes",
})


def reject_routed_input(
    allocation: dict[str, Any],
    logger: Logger | None = None,
) -> list[str]:
    """Reject allocation records that define unsupported routed topology.

    IPoIB is a link-local fabric — no gateway, static route, or RA is
    allowed per FR-3 / AC-002.

    Args:
        allocation: A single allocation record from the normalized set.
        logger: Optional validation logger.

    Returns:
        List of error strings (empty if valid).
    """
    errors: list[str] = []
    for key in _ROUTED_KEYS:
        if key in allocation and allocation[key]:
            error = (
                f"[IB-IPv6] Routed input rejected: allocation "
                f"'{allocation.get('allocation_id', '?')}' defines "
                f"'{key}' — IPoIB does not support gateway or static routes"
            )
            errors.append(error)
            if logger:
                logger.error(error)
    return errors


# ---------------------------------------------------------------------------
# nmcli command rendering (FR-3, AC-001)
# ---------------------------------------------------------------------------

def _profile_name(interface_id: str) -> str:
    """Generate a deterministic NM profile name for an IPoIB interface."""
    return f"{PROFILE_PREFIX}-{interface_id}"


def render_nmcli_commands(
    node_id: str,
    interface_id: str,
    records: list[dict[str, Any]],
    logger: Logger | None = None,
) -> dict[str, Any]:
    """Render nmcli commands for a single interface on a single node.

    Supports three modes:
    - **dual-stack**: Both IPv4 and IPv6 records present
    - **ipv6-only**: Only IPv6 records present
    - **ipv4-only**: Only IPv4 records present (legacy path)

    Args:
        node_id: Node identifier (e.g., ``nid0001``).
        interface_id: Interface identifier (e.g., ``ib0``).
        records: Allocation records for this node+interface (active only).
        logger: Optional validation logger.

    Returns:
        Dict with keys: ``profile_name``, ``mode``, ``commands``,
        ``delete_command``, ``ipoib_mode``, ``mtu``, ``pkey``.
    """
    ipv4_records = [r for r in records if r.get("address_family") == "ipv4"]
    ipv6_records = [r for r in records if r.get("address_family") == "ipv6"]

    if ipv4_records and ipv6_records:
        mode = "dual-stack"
    elif ipv6_records:
        mode = "ipv6-only"
    else:
        mode = "ipv4-only"

    profile = _profile_name(interface_id)
    # Take IPoIB-specific attributes from the first record
    first = records[0]
    ipoib_mode = first.get("ipoib_mode", "datagram")
    mtu = first.get("mtu", 2044)
    pkey = first.get("pkey", "0x8001")

    # Build the nmcli command sequence
    commands: list[str] = []

    # Step 1: Delete existing profile if present (idempotency)
    delete_cmd = f"nmcli con delete '{profile}' 2>/dev/null || true"
    commands.append(delete_cmd)

    # Step 2: Create the connection
    create_parts = [
        f"nmcli con add type infiniband con-name '{profile}'",
        f"ifname '{interface_id}'",
        f"infiniband.transport-mode {ipoib_mode}",
    ]
    if pkey and pkey != "0x8001":
        create_parts.append(f"infiniband.p-key {pkey}")

    # Step 3: IPv4 method
    if mode == "ipv6-only":
        create_parts.append("ipv4.method disabled")
    else:
        v4 = ipv4_records[0]
        v4_addr = f"{v4['address']}/{v4['prefix_length']}"
        create_parts.append("ipv4.method manual")
        create_parts.append(f"ipv4.addresses '{v4_addr}'")
        # No gateway
        create_parts.append("ipv4.never-default yes")

    # Step 4: IPv6 method
    if mode == "ipv4-only":
        create_parts.append("ipv6.method link-local")
    else:
        v6_addrs = [
            f"{r['address']}/{r['prefix_length']}" for r in ipv6_records
        ]
        create_parts.append("ipv6.method manual")
        create_parts.append(f"ipv6.addresses '{','.join(v6_addrs)}'")
        # Privacy extensions disabled (FR-3)
        create_parts.append("ipv6.ip6-privacy 0")
        # No gateway, no default route, no RA
        create_parts.append("ipv6.never-default yes")

    # Step 5: MTU
    create_parts.append(f"802-3-ethernet.mtu {mtu}")

    # Step 6: Autoconnect
    create_parts.append("connection.autoconnect yes")

    commands.append(" ".join(create_parts))

    # Step 7: Bring the connection up
    commands.append(f"nmcli con up '{profile}'")

    result = {
        "profile_name": profile,
        "mode": mode,
        "commands": commands,
        "delete_command": delete_cmd,
        "ipoib_mode": ipoib_mode,
        "mtu": mtu,
        "pkey": pkey,
        "node_id": node_id,
        "interface_id": interface_id,
    }

    if logger:
        logger.info(
            "[IB-IPv6] NM renderer: %s/%s → profile=%s mode=%s",
            node_id, interface_id, profile, mode,
        )

    return result


def render_node_nmcli(
    node_id: str,
    interfaces: dict[str, list[dict[str, Any]]],
    logger: Logger | None = None,
) -> list[dict[str, Any]]:
    """Render nmcli commands for all interfaces on a node.

    Args:
        node_id: Node identifier.
        interfaces: Per-interface allocation records (from normalize_per_node).
        logger: Optional validation logger.

    Returns:
        List of per-interface render results.
    """
    results = []
    for interface_id in sorted(interfaces.keys()):
        records = interfaces[interface_id]
        # Reject routed input for each record
        routed_errors = []
        for record in records:
            routed_errors.extend(reject_routed_input(record, logger))
        if routed_errors:
            results.append({
                "profile_name": _profile_name(interface_id),
                "mode": "error",
                "errors": routed_errors,
                "node_id": node_id,
                "interface_id": interface_id,
            })
            continue
        results.append(
            render_nmcli_commands(node_id, interface_id, records, logger)
        )
    return results


# ---------------------------------------------------------------------------
# Cloud-init user-data rendering (Task 2)
# ---------------------------------------------------------------------------

def render_cloud_init_script(
    node_id: str,
    nm_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Render cloud-init write_files + runcmd entries for nmcli commands.

    Generates the cloud-init user-data structure that delivers the nmcli
    configuration script to each node at first boot.

    Args:
        node_id: Node identifier.
        nm_results: Output of ``render_node_nmcli`` (list of per-interface dicts).

    Returns:
        Dict with keys ``write_files`` and ``runcmd`` for cloud-init merge.
    """
    script_lines = [
        "#!/bin/bash",
        f"{MANAGED_MARKER}",
        f"# IPoIB IPv6 configuration for {node_id}",
        "set -euo pipefail",
        "",
    ]

    for result in nm_results:
        if result.get("mode") == "error":
            continue
        script_lines.append(
            f"# Interface: {result['interface_id']} "
            f"(mode: {result['mode']})"
        )
        for cmd in result["commands"]:
            script_lines.append(cmd)
        script_lines.append("")

    script_content = "\n".join(script_lines)
    script_path = f"/var/lib/omnia/scripts/configure-ipoib-{node_id}.sh"

    return {
        "write_files": [
            {
                "path": script_path,
                "permissions": "0755",
                "content": script_content,
            },
        ],
        "runcmd": [
            f"bash {script_path}",
        ],
    }


# ---------------------------------------------------------------------------
# SMD Renderer (Tasks 4-5)
# ---------------------------------------------------------------------------

def render_smd_interfaces(
    node_id: str,
    interfaces: dict[str, list[dict[str, Any]]],
    logger: Logger | None = None,
) -> list[dict[str, Any]]:
    """Render SMD component interface payloads from normalized allocations.

    Each logical IPoIB interface produces an SMD EthernetInterface entry
    with all applicable approved addresses.

    Args:
        node_id: Node identifier (xname).
        interfaces: Per-interface allocation records.
        logger: Optional validation logger.

    Returns:
        List of SMD EthernetInterface payloads.
    """
    smd_interfaces = []
    for interface_id in sorted(interfaces.keys()):
        records = interfaces[interface_id]
        ipv4_addrs = []
        ipv6_addrs = []
        for record in records:
            if record.get("address_family") == "ipv4":
                ipv4_addrs.append(
                    {"IPAddress": record["address"]}
                )
            else:
                ipv6_addrs.append(
                    {"IPAddress": record["address"]}
                )

        smd_iface: dict[str, Any] = {
            "ID": f"{node_id}-{interface_id}",
            "Description": f"IPoIB {interface_id}",
            "InterfaceType": "EthernetInterface",
            "ComponentID": node_id,
        }
        if ipv4_addrs:
            smd_iface["IPV4Addresses"] = ipv4_addrs
        if ipv6_addrs:
            smd_iface["IPV6Addresses"] = ipv6_addrs

        smd_interfaces.append(smd_iface)

        if logger:
            logger.info(
                "[IB-IPv6] SMD renderer: %s/%s → %d IPv4, %d IPv6 addresses",
                node_id, interface_id, len(ipv4_addrs), len(ipv6_addrs),
            )

    return smd_interfaces


def render_smd_component(
    node_id: str,
    hostname: str,
    interfaces: dict[str, list[dict[str, Any]]],
    logger: Logger | None = None,
) -> dict[str, Any]:
    """Render a complete SMD component payload for a node.

    Args:
        node_id: Node xname.
        hostname: Node hostname.
        interfaces: Per-interface allocation records.
        logger: Optional validation logger.

    Returns:
        SMD Component payload dict.
    """
    return {
        "ID": node_id,
        "Type": "Node",
        "Hostname": hostname,
        "NetType": "InfiniBand",
        "Interfaces": render_smd_interfaces(node_id, interfaces, logger),
    }


# ---------------------------------------------------------------------------
# Managed Hosts Renderer (Tasks 7-8)
# ---------------------------------------------------------------------------

def render_hostname_entry(
    record: dict[str, Any],
    is_single_interface: bool,
) -> str:
    """Render a single /etc/hosts entry from an allocation record.

    Hostname convention (from ER FR-4):
    - Canonical: ``<hostname>-<interface_id>`` (e.g., ``nid0001-ib0``)
    - Single-interface alias: ``<hostname>-ib``

    Args:
        record: Single allocation record with ``address``, ``hostname``,
                ``interface_id``.
        is_single_interface: Whether the node has only one IPoIB interface.

    Returns:
        Hosts file line (e.g., ``fd00:1b::1  nid0001-ib0 nid0001-ib``).
    """
    address = record["address"]
    hostname = record["hostname"]
    interface_id = record["interface_id"]

    canonical = f"{hostname}-{interface_id}"
    parts = [address, canonical]

    if is_single_interface:
        parts.append(f"{hostname}-ib")

    return "\t".join(parts)


def render_managed_hosts_block(
    all_active_nodes: dict[str, dict[str, list[dict[str, Any]]]],
    logger: Logger | None = None,
) -> str:
    """Render the managed /etc/hosts block from the complete active snapshot.

    The block contains entries for ALL active allocations in the cluster,
    not just the nodes being provisioned. The block is delimited by markers
    so it can be atomically replaced without disturbing user-managed content.

    Args:
        all_active_nodes: Complete per-node, per-interface allocation set.
        logger: Optional validation logger.

    Returns:
        Multi-line string with the managed hosts block (including markers).
    """
    lines = [HOSTS_BEGIN_MARKER]
    entry_count = 0

    for node_id in sorted(all_active_nodes.keys()):
        interfaces = all_active_nodes[node_id]
        is_single = len(interfaces) == 1

        for interface_id in sorted(interfaces.keys()):
            for record in interfaces[interface_id]:
                entry = render_hostname_entry(record, is_single)
                lines.append(entry)
                entry_count += 1

    lines.append(HOSTS_END_MARKER)

    if logger:
        logger.info(
            "[IB-IPv6] Hosts renderer: %d entries across %d nodes",
            entry_count, len(all_active_nodes),
        )

    return "\n".join(lines)


def apply_managed_hosts_block(
    existing_content: str,
    new_block: str,
) -> str:
    """Replace the managed block in /etc/hosts, preserving user content.

    If the managed block markers exist, replace between them.
    If not, append the block at the end.

    Args:
        existing_content: Current /etc/hosts content.
        new_block: New managed block (with markers).

    Returns:
        Updated /etc/hosts content.
    """
    begin_idx = existing_content.find(HOSTS_BEGIN_MARKER)
    end_idx = existing_content.find(HOSTS_END_MARKER)

    if begin_idx >= 0 and end_idx >= 0:
        # Replace existing block
        end_of_marker = end_idx + len(HOSTS_END_MARKER)
        # Consume trailing newline if present
        if end_of_marker < len(existing_content) and \
                existing_content[end_of_marker] == "\n":
            end_of_marker += 1
        return existing_content[:begin_idx] + new_block + "\n" + \
            existing_content[end_of_marker:]

    # Append at end
    if existing_content and not existing_content.endswith("\n"):
        return existing_content + "\n" + new_block + "\n"
    return existing_content + new_block + "\n"


# ---------------------------------------------------------------------------
# Idempotent reapplication (Task 9, AC-006)
# ---------------------------------------------------------------------------

def compute_config_hash(nm_results: list[dict[str, Any]]) -> str:
    """Compute a deterministic hash of the NM configuration for a node.

    Used to detect whether the configuration has changed between runs.
    If the hash matches the previous run, the reapplication is a no-op.

    Args:
        nm_results: Output of ``render_node_nmcli``.

    Returns:
        Hex digest string.
    """
    import hashlib
    parts = []
    for result in sorted(nm_results, key=lambda r: r.get("interface_id", "")):
        if result.get("mode") == "error":
            continue
        parts.append(result["profile_name"])
        parts.append(result["mode"])
        parts.extend(result.get("commands", []))
    content = "\n".join(parts)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def is_reapplication_needed(
    current_hash: str,
    previous_hash: str | None,
) -> bool:
    """Determine whether reapplication is needed.

    Args:
        current_hash: Hash of the current configuration.
        previous_hash: Hash from the previous run (or None if first run).

    Returns:
        True if configuration changed and reapplication is needed.
    """
    if previous_hash is None:
        return True
    return current_hash != previous_hash


# ---------------------------------------------------------------------------
# Full pipeline orchestrator
# ---------------------------------------------------------------------------

def render_node_full(
    node_id: str,
    interfaces: dict[str, list[dict[str, Any]]],
    logger: Logger | None = None,
) -> dict[str, Any]:
    """Orchestrate the full rendering pipeline for a single node.

    Chains NM renderer → cloud-init renderer → SMD renderer, collecting
    all outputs and errors.

    Args:
        node_id: Node identifier.
        interfaces: Per-interface allocation records.
        logger: Optional validation logger.

    Returns:
        Dict with keys: ``node_id``, ``nm_results``, ``cloud_init``,
        ``smd_interfaces``, ``config_hash``, ``errors``.
    """
    hostname = None
    for iface_records in interfaces.values():
        for r in iface_records:
            hostname = r.get("hostname", node_id)
            break
        if hostname:
            break
    if not hostname:
        hostname = node_id

    nm_results = render_node_nmcli(node_id, interfaces, logger)

    errors = []
    for result in nm_results:
        if result.get("mode") == "error":
            errors.extend(result.get("errors", []))

    cloud_init = render_cloud_init_script(node_id, nm_results)
    smd_ifaces = render_smd_interfaces(node_id, interfaces, logger)
    smd_component = render_smd_component(
        node_id, hostname, interfaces, logger
    )
    config_hash = compute_config_hash(nm_results)

    return {
        "node_id": node_id,
        "hostname": hostname,
        "nm_results": nm_results,
        "cloud_init": cloud_init,
        "smd_interfaces": smd_ifaces,
        "smd_component": smd_component,
        "config_hash": config_hash,
        "errors": errors,
    }
