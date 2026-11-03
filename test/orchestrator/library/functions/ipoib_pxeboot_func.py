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

"""ER-ORCH-005 post-boot IPoIB verification for every ib_addr_mode.

ib_addr_mode selects the address families IPoIB carries: ipv4-only assigns
IB IPv4, ipv6-only assigns IB IPv6, and dual-stack assigns both on the same
interface. Every check validates each family the active mode selects, so the
same suite verifies any mode instead of skipping the ones it was not written
for. Slurm checks use the family Slurm NodeAddr resolves to.
"""

import os
import re
import shlex
from typing import Any

from ..vars.ipoib_vars import (
    DYNAMIC_ADDRESS_FLAGS,
    IB_MODE_FAMILIES,
    IPOIB_COMMANDS,
    IPV6_MODES,
    NETWORK_SPEC_FILE,
    NM_EXPECTED_METHODS,
    NM_PRIVACY_DISABLED,
    NM_PROFILE_FIELDS,
    PING_TIMEOUT_SECONDS,
    SLURM_CONFIG_SOURCE,
    SLURM_CONFIG_SOURCES_KEY,
    SLURM_ENABLE_IPV6,
    SLURM_STATE_FLAG_SUFFIXES,
    SLURM_UNRESPONSIVE_STATES,
    UNHEALTHY_IPV6_FLAGS,
)
from ..vars.pxeboot_vars import PXEBOOT_COMMANDS, SLURM_COMPUTE_PREFIX
from ._ipoib_helpers import (
    canonical_ip,
    ib_addr_mode,
    ib_network_block,
    prefix_length,
    row_address,
    slurm_family,
)
from ._ipoib_runtime_helpers import (
    full_mesh,
    ib_interface,
    interface_addresses,
    interface_names,
    mesh_failures,
)
from ._prepare_helpers import read_yaml_mapping
from ._provision_helpers import api_json, interface_ips, load_context, resource_list
from ._pxeboot_helpers import (
    remote_command,
    remote_json,
    runtime_exception,
    runtime_result,
)
from ._workload_helpers import optional_skip, slurm_context
from .project_func import resolve_target_input_project_path

_ERRORS = (OSError, RuntimeError, TypeError, ValueError, KeyError)


def _default_prefix(value) -> int | None:
    bits = str(value or "").strip()
    return int(bits) if bits.isdigit() else None


def _ipoib_nodes(host):
    """Return (mode, nodes); each node carries row, ipv4/ipv6, and prefix4/prefix6."""
    context = load_context(host)
    input_dir = resolve_target_input_project_path(host)
    block = ib_network_block(
        read_yaml_mapping(host, os.path.join(input_dir, NETWORK_SPEC_FILE))
    )
    default_prefix6 = _default_prefix(block.get("ipv6_netmask_bits"))
    default_prefix4 = _default_prefix(
        block.get("ipv4_netmask_bits", block.get("netmask_bits"))
    )
    nodes = []
    for row in context["rows"]:
        if not str(row.get("IB_NIC_NAME") or "").strip():
            continue
        raw4, raw6 = row_address(row, 4), row_address(row, 6)
        nodes.append(
            {
                "row": row,
                "ipv4": canonical_ip(raw4),
                "ipv6": canonical_ip(raw6),
                "prefix4": prefix_length(raw4) or default_prefix4,
                "prefix6": prefix_length(raw6) or default_prefix6,
            }
        )
    return ib_addr_mode(block), nodes


def _mode_selection(host, summary, minimum=1):
    """Return (mode, families, nodes, early_result) for the active ib_addr_mode.

    Selects IB nodes that hold an approved address for every family the mode
    assigns. Nodes with an incomplete allocation are reported by the mode
    address assignment check, so they are not re-reported here.
    """
    mode, nodes = _ipoib_nodes(host)
    families = IB_MODE_FAMILIES.get(mode)
    if families is None:
        return mode, (), [], runtime_result(
            False, summary, [("IB mode", mode)], f"Unsupported ib_addr_mode {mode}"
        )
    selected = [node for node in nodes if all(node[f"ipv{f}"] for f in families)]
    if len(selected) < minimum:
        wanted = " and ".join(f"IB_IPV{f}" for f in families)
        return mode, families, [], optional_skip(
            summary,
            f"At least {minimum} mapped node(s) with IB_NIC_NAME and {wanted} "
            f"are required for {mode}",
        )
    return mode, families, selected, None


def _family_label(families) -> str:
    return " + ".join(f"IPv{family}" for family in families)


def _addr_info(iface, address: str) -> dict[str, Any] | None:
    for info in (iface or {}).get("addr_info", []):
        if isinstance(info, dict) and canonical_ip(info.get("local")) == address:
            return info
    return None


def _locate(payload, address: str):
    """Return (interface, addr_info) carrying *address* in an ``ip -j addr`` payload."""
    for iface in payload if isinstance(payload, list) else []:
        info = _addr_info(iface, address) if isinstance(iface, dict) else None
        if info is not None:
            return iface, info
    return None, None


def _finish(summary, results, error_prefix):
    fields: list[tuple[str, object]] = [("Nodes checked", len(results))]
    failed = []
    for node, success, details in results:
        row = node["row"]
        fields.append((f"  {row['HOSTNAME']}", f"{'✓' if success else '✗'} {row['ADMIN_IP']}"))
        fields.extend((f"    {label}", value) for label, value in details)
        if not success:
            failed.append(row["HOSTNAME"])
    error = f"{error_prefix}: {', '.join(failed)}" if failed else ""
    return runtime_result(not failed, summary, fields, error)


# ---------------------------------------------------------------------------
# Address assignment and address health
# ---------------------------------------------------------------------------


def _assignment_problems(node, families, payload) -> tuple[list[str], list[str]]:
    """Compare a node's live addresses with the families its mode assigns."""
    problems = []
    located = []
    for family in families:
        address = node[f"ipv{family}"]
        if not address:
            problems.append(f"mapping has no IB IPv{family}")
            continue
        iface, info = _locate(payload, address)
        if iface is None:
            problems.append(f"IB IPv{family} {address} not assigned")
            continue
        located.append(iface)
        prefix = node[f"prefix{family}"]
        if prefix and info.get("prefixlen") != prefix:
            problems.append(f"IPv{family} prefix /{info.get('prefixlen')} != /{prefix}")
    names = sorted({str(iface.get("ifname", "")) for iface in located})
    if len(names) > 1:
        problems.append("IB IPv4 and IPv6 are on different interfaces")
    for family in sorted({4, 6} - set(families)):
        mapped = node[f"ipv{family}"]
        if mapped and _locate(payload, mapped)[0] is not None:
            problems.append(f"mapped IPv{family} {mapped} assigned although the mode excludes it")
        extras = sorted({a for iface in located for a in interface_addresses(iface, family)})
        if extras:
            problems.append(f"unexpected IPv{family} on IB interface: " + ", ".join(extras))
    return problems, names


def check_ipoib_mode_address_assignment(host) -> dict[str, Any]:
    """Each IB node carries exactly the IB addresses its ib_addr_mode selects.

    ipv4-only: IB IPv4 only; ipv6-only: IB IPv6 only; dual-stack: both on the
    same interface. A mapped address of an excluded family must not be assigned.
    """
    summary = "IPoIB mode address assignment"
    try:
        mode, nodes = _ipoib_nodes(host)
        families = IB_MODE_FAMILIES.get(mode)
        if families is None:
            return runtime_result(
                False, summary, [("IB mode", mode)], f"Unsupported ib_addr_mode {mode}"
            )
        if not nodes:
            return optional_skip(summary, "No mapped node has IB_NIC_NAME")
        results = []
        for node in nodes:
            payload = remote_json(host, node["row"], IPOIB_COMMANDS["ip_addresses"])
            problems, names = _assignment_problems(node, families, payload)
            expected = ", ".join(node[f"ipv{f}"] or f"<no IB IPv{f}>" for f in families)
            results.append(
                (
                    node,
                    not problems,
                    [
                        ("Mode", mode),
                        ("Expected", expected),
                        ("Interface", ", ".join(names) or "not found"),
                        ("Result", "matches mode" if not problems else "; ".join(problems)),
                    ],
                )
            )
        return _finish(summary, results, "IB address assignment does not match mode on")
    except _ERRORS as exc:
        return runtime_exception(summary, exc)


def _address_health(node, iface, family) -> tuple[str, list[str]]:
    """Return (display, problems) for one approved address on the IB interface."""
    approved = node[f"ipv{family}"]
    info = _addr_info(iface, approved)
    if info is None:
        return f"{approved} not configured", [f"IPv{family} {approved} not configured"]
    problems = []
    prefix = node[f"prefix{family}"]
    if prefix and info.get("prefixlen") != prefix:
        problems.append(f"IPv{family} prefix /{info.get('prefixlen')} != /{prefix}")
    if family == 6:
        problems.extend(f"IPv6 flag {flag}" for flag in UNHEALTHY_IPV6_FLAGS if info.get(flag))
    if any(info.get(flag) for flag in DYNAMIC_ADDRESS_FLAGS):
        problems.append(f"IPv{family} {approved} is not static")
    extras = sorted(interface_addresses(iface, family) - {approved})
    if extras:
        problems.append(f"unexpected global IPv{family}: " + ", ".join(extras))
    return f"{approved}/{info.get('prefixlen')}", problems


def check_ipoib_address_state(host) -> dict[str, Any]:
    """TC-FVT-015/017: each approved IB address is static, healthy, and alone.

    For every family the mode assigns: the approved address carries the
    approved prefix, is static (not DHCP/SLAAC), is the only global address of
    that family on the IB interface, and for IPv6 is DAD-clean and preferred.
    """
    summary = "IPoIB address state"
    try:
        mode, families, nodes, early = _mode_selection(host, summary)
        if early:
            return early
        results = []
        for node in nodes:
            iface, name = ib_interface(host, node)
            if iface is None:
                results.append((node, False, [("Interface", "no interface carries an IB address")]))
                continue
            details = [("Mode", mode), ("Interface", name)]
            problems = []
            for family in families:
                display, family_problems = _address_health(node, iface, family)
                details.append((f"IPv{family}", display))
                problems.extend(family_problems)
            details.append(("Result", "HEALTHY" if not problems else "; ".join(problems)))
            results.append((node, not problems, details))
        return _finish(summary, results, f"IPoIB {_family_label(families)} address state failed on")
    except _ERRORS as exc:
        return runtime_exception(summary, exc)


# ---------------------------------------------------------------------------
# NetworkManager profile
# ---------------------------------------------------------------------------


def _nm_values(stdout: str) -> dict[str, str]:
    lines = [line.replace("\\:", ":").strip() for line in stdout.splitlines()]
    lines += [""] * (len(NM_PROFILE_FIELDS) - len(lines))
    return dict(zip(NM_PROFILE_FIELDS, lines))


def _nm_addresses(value: str) -> set[tuple[str, int | None]]:
    return {
        (canonical_ip(entry), prefix_length(entry))
        for entry in value.split(",")
        if canonical_ip(entry)
    }


def _nm_problems(mode, families, node, values) -> list[str]:
    """Compare a profile with what configure-ib-network.sh sets for *mode*."""
    problems = [
        f"{key}={values[key] or '<empty>'} (expected {expected})"
        for key, expected in NM_EXPECTED_METHODS[mode].items()
        if values[key] != expected
    ]
    for family in (4, 6):
        key = f"ipv{family}.addresses"
        configured = _nm_addresses(values[key])
        if family not in families:
            if configured:
                problems.append(f"{key}={values[key]} although {mode} excludes IPv{family}")
            continue
        approved, prefix = node[f"ipv{family}"], node[f"prefix{family}"]
        if not any(addr == approved and (prefix is None or bits == prefix)
                   for addr, bits in configured):
            expected = f"{approved}/{prefix}" if prefix else approved
            problems.append(f"{key} lacks {expected}")
    if 6 in families and values["ipv6.ip6-privacy"] not in NM_PRIVACY_DISABLED:
        problems.append(f"ipv6.ip6-privacy={values['ipv6.ip6-privacy'] or '<empty>'}")
    problems.extend(
        f"{key}={values[key]}" for key in ("ipv4.gateway", "ipv6.gateway") if values[key]
    )
    return problems


def check_ipoib_nm_profile(host) -> dict[str, Any]:
    """TC-FVT-002/009: the IB NetworkManager profile matches ib_addr_mode.

    Methods follow the mode, every assigned family carries its approved
    address, excluded families carry none, IPv6 privacy is off whenever IPv6
    is assigned, and no gateway is configured.
    """
    summary = "IPoIB NetworkManager profile"
    try:
        mode, families, nodes, early = _mode_selection(host, summary)
        if early:
            return early
        results = []
        for node in nodes:
            _iface, name = ib_interface(host, node)
            if not name:
                results.append((node, False, [("Profile", "IB interface not found")]))
                continue
            out = remote_command(
                host, node["row"], IPOIB_COMMANDS["nm_profile"] % shlex.quote(name)
            )
            if out.rc != 0:
                results.append((node, False, [("Profile", f"{name} not found")]))
                continue
            values = _nm_values(out.stdout)
            problems = _nm_problems(mode, families, node, values)
            results.append(
                (
                    node,
                    not problems,
                    [
                        ("Mode", mode),
                        ("Profile", name),
                        *[(key, values[key] or "<empty>") for key in NM_PROFILE_FIELDS],
                        ("Result", "matches mode" if not problems else "; ".join(problems)),
                    ],
                )
            )
        return _finish(summary, results, "NetworkManager profile does not match mode on")
    except _ERRORS as exc:
        return runtime_exception(summary, exc)


# ---------------------------------------------------------------------------
# Routing and peer reachability
# ---------------------------------------------------------------------------


def _route_problems(host, node, name, family, peer) -> tuple[list[str], str]:
    """Return (problems, peer-route display) for one family on the IB interface."""
    row = node["row"]
    routes = remote_json(
        host, row, IPOIB_COMMANDS["routes_on_dev"] % (family, shlex.quote(name))
    )
    defaults = remote_json(host, row, IPOIB_COMMANDS["default_routes"] % family)
    problems = [
        f"IPv{family} route {route.get('dst')} via {route.get('gateway')}"
        for route in routes or []
        if route.get("dst") != "default" and route.get("gateway")
    ]
    problems.extend(
        f"IPv{family} default route on {name}"
        for route in defaults or []
        if route.get("dev") == name
    )
    if peer is None:
        return problems, "no peer"
    target, source = peer[f"ipv{family}"], node[f"ipv{family}"]
    lookup = remote_json(host, row, IPOIB_COMMANDS["route_to"] % (family, shlex.quote(target)))
    entry = lookup[0] if isinstance(lookup, list) and lookup else {}
    display = f"{target} dev {entry.get('dev')} src {entry.get('prefsrc')}"
    if entry.get("gateway"):
        problems.append(f"IPv{family} peer {target} routed via gateway {entry['gateway']}")
    if entry.get("dev") != name or canonical_ip(entry.get("prefsrc")) != source:
        problems.append(f"IPv{family} peer {target} not routed via {name} from {source}")
    return problems, display


def check_ipoib_routes(host) -> dict[str, Any]:
    """TC-FVT-009/015: IPoIB is on-link only for every family the mode assigns.

    No gateway or default route uses the IB interface, and a peer's approved
    address is reached directly over the IB interface from the approved source.
    """
    summary = "IPoIB routing"
    try:
        mode, families, nodes, early = _mode_selection(host, summary)
        if early:
            return early
        results = []
        for position, node in enumerate(nodes):
            _iface, name = ib_interface(host, node)
            if not name:
                results.append((node, False, [("Routes", "IB interface not found")]))
                continue
            peer = nodes[(position + 1) % len(nodes)] if len(nodes) > 1 else None
            details = [("Mode", mode), ("Interface", name)]
            problems = []
            for family in families:
                family_problems, display = _route_problems(host, node, name, family, peer)
                details.append((f"IPv{family} peer route", display))
                problems.extend(family_problems)
            details.append(("Result", "on-link only" if not problems else "; ".join(problems)))
            results.append((node, not problems, details))
        return _finish(summary, results, "IPoIB routing violation on")
    except _ERRORS as exc:
        return runtime_exception(summary, exc)


def check_ipoib_peer_mesh(host) -> dict[str, Any]:
    """TC-FVT-023: every IB node reaches every peer in each family the mode assigns."""
    summary = "IPoIB peer reachability"
    try:
        mode, families, nodes, early = _mode_selection(host, summary, minimum=2)
        if early:
            return early
        names = interface_names(host, nodes)
        pairs = full_mesh(nodes)
        results = []
        for source in nodes:
            outgoing = [(src, dst) for src, dst in pairs if src is source]
            unreachable = mesh_failures(host, outgoing, families, names)
            results.append(
                (
                    source,
                    not unreachable,
                    [
                        ("Mode", mode),
                        ("Interface", names.get(source["row"]["HOSTNAME"]) or "missing"),
                        ("Probes", f"{len(outgoing)} peers x {_family_label(families)}"),
                        ("Unreachable", ", ".join(unreachable) or "none"),
                    ],
                )
            )
        return _finish(summary, results, "IPoIB peers unreachable from")
    except _ERRORS as exc:
        return runtime_exception(summary, exc)


# ---------------------------------------------------------------------------
# SMD publication
# ---------------------------------------------------------------------------


def check_ipoib_smd_records(host) -> dict[str, Any]:
    """TC-FVT-011: SMD holds every approved IPoIB address of each node."""
    summary = "IPoIB SMD publication"
    try:
        mode, families, nodes, early = _mode_selection(host, summary)
        if early:
            return early
        interfaces = resource_list(api_json(host, "ethernet"))
        published = {
            canonical_ip(address) for interface in interfaces
            for address in interface_ips(interface)
        }
        by_component: dict[str, set[str]] = {}
        component_of_ip: dict[str, str] = {}
        for interface in interfaces:
            component = str(interface.get("ComponentID") or "")
            for address in interface_ips(interface):
                by_component.setdefault(component, set()).add(canonical_ip(address))
                component_of_ip[canonical_ip(address)] = component
        results = []
        for node in nodes:
            expected = [node[f"ipv{f}"] for f in families]
            missing = [address for address in expected if address not in published]
            component = component_of_ip.get(canonical_ip(node["row"]["ADMIN_IP"]), "")
            recorded = sorted(by_component.get(component, set())) if component else []
            results.append(
                (
                    node,
                    not missing,
                    [
                        ("Mode", mode),
                        ("Expected", ", ".join(expected)),
                        (f"SMD addresses for {component or 'node'}",
                         ", ".join(recorded) or "none"),
                        ("Missing in SMD", ", ".join(missing) or "none"),
                    ],
                )
            )
        return _finish(summary, results, "SMD is missing IPoIB addresses for")
    except _ERRORS as exc:
        return runtime_exception(summary, exc)


# ---------------------------------------------------------------------------
# Slurm
# ---------------------------------------------------------------------------


def _scontrol_nodeaddr(stdout: str) -> dict[str, str]:
    mapping = {}
    for line in stdout.splitlines():
        name = re.search(r"\bNodeName=(\S+)", line)
        address = re.search(r"\bNodeAddr=(\S+)", line)
        if name and address:
            mapping[name.group(1)] = address.group(1)
    return mapping


def _expected_nodeaddr(mode: str, row) -> tuple[set[str], str]:
    """Return the NodeAddr the mode selects.

    ipv6-only and dual-stack use the IB IPv6; ipv4-only uses the IB IPv4 even
    when IB_IPV6 is populated. Rows without IB columns keep the hostname.
    """
    if not str(row.get("IB_NIC_NAME") or "").strip():
        return {row["HOSTNAME"]}, "unset (no IB columns)"
    family = slurm_family(mode)
    address = canonical_ip(row_address(row, family))
    return ({address} if address else set()), f"approved IB IPv{family} ({mode})"


def _communication_parameters(stdout: str) -> set[str]:
    for line in stdout.splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() == "CommunicationParameters":
            return {item.strip() for item in value.split(",") if item.strip() not in {"", "(null)"}}
    return set()


def _enable_ipv6_result(host, control, mode):
    """Controller row: EnableIPv6 must be set whenever the mode selects IPv6."""
    out = remote_command(host, control, IPOIB_COMMANDS["slurm_show_config"])
    if out.rc != 0:
        return (
            {"row": control}, False,
            [("CommunicationParameters", "scontrol show config failed")],
        )
    params = _communication_parameters(out.stdout)
    required = mode in IPV6_MODES
    success = SLURM_ENABLE_IPV6 in params or not required
    return (
        {"row": control},
        success,
        [
            ("CommunicationParameters", ",".join(sorted(params)) or "<unset>"),
            ("Expected", f"{SLURM_ENABLE_IPV6} ({mode})" if required else f"not required ({mode})"),
        ],
    )


def check_ipoib_slurm_nodeaddr(host) -> dict[str, Any]:
    """TC-FVT-019/031: NodeAddr follows the mode's IB address; EnableIPv6 for IPv6 modes."""
    summary = "Slurm IPoIB NodeAddr"
    try:
        context, rows, control, _config = slurm_context(host)
        compute = [
            row for row in rows
            if row["EXPECTED_FUNCTIONAL_GROUP"].startswith(SLURM_COMPUTE_PREFIX)
        ]
        if control is None or not compute:
            return optional_skip(summary, "No Slurm compute nodes are mapped")
        mode = ib_addr_mode(ib_network_block(context["network_spec"]))
        out = remote_command(host, control, PXEBOOT_COMMANDS["slurm_nodes"])
        if out.rc != 0:
            return runtime_result(
                False, summary, [], "scontrol show nodes failed on the Slurm controller"
            )
        actual = _scontrol_nodeaddr(out.stdout)
        results = []
        for row in compute:
            expected, label = _expected_nodeaddr(mode, row)
            value = actual.get(row["HOSTNAME"], "")
            success = (canonical_ip(value) or value) in expected
            results.append(
                (
                    {"row": row},
                    success,
                    [
                        ("Expected",
                         f"{label}: {', '.join(sorted(expected)) or '<missing in mapping>'}"),
                        ("NodeAddr", value or "node not in scontrol"),
                    ],
                )
            )
        results.append(_enable_ipv6_result(host, control, mode))
        return _finish(summary, results, "Unexpected Slurm NodeAddr or CommunicationParameters for")
    except _ERRORS as exc:
        return runtime_exception(summary, exc)


def _node_states(stdout: str) -> dict[str, str]:
    states = {}
    for line in stdout.splitlines():
        parts = line.split("|")
        if len(parts) >= 4:
            states[parts[0].strip()] = parts[2].strip().lower()
    return states


def check_ipoib_custom_slurm_conf(host) -> dict[str, Any]:
    """TC-FVT-027: with a user slurm.conf, nodes respond and IB reaches them."""
    summary = "Custom slurm.conf with IPoIB"
    try:
        context, rows, control, config = slurm_context(host)
        sources = (config or {}).get(SLURM_CONFIG_SOURCES_KEY) or {}
        if control is None or not sources.get(SLURM_CONFIG_SOURCE):
            return optional_skip(
                summary, "slurm_cluster config_sources does not provide slurm.conf"
            )
        mode = ib_addr_mode(ib_network_block(context["network_spec"]))
        family = slurm_family(mode)
        states = remote_command(host, control, PXEBOOT_COMMANDS["slurm_partitions"])
        if states.rc != 0:
            return runtime_result(False, summary, [], "sinfo failed on the Slurm controller")
        node_state = _node_states(states.stdout)
        results = []
        for row in rows:
            if not row["EXPECTED_FUNCTIONAL_GROUP"].startswith(SLURM_COMPUTE_PREFIX):
                continue
            state = node_state.get(row["HOSTNAME"], "missing")
            responsive = (
                state != "missing"
                and "*" not in state
                and state.rstrip(SLURM_STATE_FLAG_SUFFIXES) not in SLURM_UNRESPONSIVE_STATES
            )
            has_ib = bool(str(row.get("IB_NIC_NAME") or "").strip())
            target = canonical_ip(row_address(row, family)) if has_ib else ""
            reach = "not mapped"
            if target:
                probe = remote_command(
                    host,
                    control,
                    IPOIB_COMMANDS["ping"] % (family, PING_TIMEOUT_SECONDS, shlex.quote(target)),
                )
                reach = "reachable" if probe.rc == 0 else "unreachable"
            results.append(
                (
                    {"row": row},
                    responsive and reach != "unreachable",
                    [("Slurm state", state), (f"IB IPv{family} {target or '-'}", reach)],
                )
            )
        return _finish(summary, results, "Custom slurm.conf node not healthy over IB")
    except _ERRORS as exc:
        return runtime_exception(summary, exc)
