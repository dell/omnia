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

"""ER-ORCH-005 post-boot IPoIB IPv6 verification on mapped nodes."""

import os
import re
import shlex
from typing import Any

from ..vars.ipoib_vars import (
    AUTONOMOUS_IPV6_FLAGS,
    IB_MODE_DUAL_STACK,
    IB_MODE_FAMILIES,
    IPOIB_COMMANDS,
    IPV6_MODES,
    NETWORK_SPEC_FILE,
    NM_EXPECTED_METHODS,
    NM_PRIVACY_DISABLED,
    NM_PROFILE_FIELDS,
    PING_TIMEOUT_SECONDS,
    SAFE_IFACE,
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


def _ipv6_selection(host, summary, minimum=1):
    mode, nodes = _ipoib_nodes(host)
    if mode not in IPV6_MODES:
        skip = optional_skip(summary, f"ib_addr_mode is {mode}; IPv6 IPoIB is not selected")
        return mode, None, skip
    selected = [node for node in nodes if node["ipv6"]]
    if len(selected) < minimum:
        skip = optional_skip(
            summary,
            f"At least {minimum} mapped node(s) with IB_NIC_NAME and IB_IPV6 are required",
        )
        return mode, None, skip
    return mode, selected, None


def _locate(payload, address: str):
    for iface in payload if isinstance(payload, list) else []:
        for info in iface.get("addr_info", []) if isinstance(iface, dict) else []:
            if isinstance(info, dict) and canonical_ip(info.get("local")) == address:
                return iface, info
    return None, None


def _ib_iface(host, node):
    """Return the interface carrying the approved IPv6, its addr_info, and name."""
    payload = remote_json(host, node["row"], IPOIB_COMMANDS["ip_addresses"])
    iface, info = _locate(payload, node["ipv6"])
    name = str(iface.get("ifname", "")) if iface else ""
    if name and not SAFE_IFACE.fullmatch(name):
        raise ValueError(f"{node['row']['HOSTNAME']} reported an unsafe interface name")
    return iface, info, name


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


def _address_problems(node, iface, info) -> list[str]:
    problems = []
    if node["prefix6"] and info.get("prefixlen") != node["prefix6"]:
        problems.append(f"prefix /{info.get('prefixlen')} != /{node['prefix6']}")
    problems.extend(f"flag {flag}" for flag in UNHEALTHY_IPV6_FLAGS if info.get(flag))
    if any(info.get(flag) for flag in AUTONOMOUS_IPV6_FLAGS):
        problems.append("approved address is not static")
    extras = [
        str(entry.get("local"))
        for entry in iface.get("addr_info", [])
        if entry.get("family") == "inet6"
        and entry.get("scope") == "global"
        and canonical_ip(entry.get("local")) != node["ipv6"]
    ]
    if extras:
        problems.append("unexpected global IPv6: " + ", ".join(extras))
    return problems


def check_ipoib_ipv6_address_state(host) -> dict[str, Any]:
    """TC-FVT-015/017: approved IPv6 is static, preferred, DAD-clean, and alone."""
    summary = "IPoIB IPv6 address state"
    try:
        _mode, nodes, skip = _ipv6_selection(host, summary)
        if skip:
            return skip
        results = []
        for node in nodes:
            iface, info, name = _ib_iface(host, node)
            if iface is None:
                results.append((node, False, [("Address", f"{node['ipv6']} not configured")]))
                continue
            problems = _address_problems(node, iface, info)
            results.append(
                (
                    node,
                    not problems,
                    [
                        ("Interface", name),
                        ("Address", f"{node['ipv6']}/{info.get('prefixlen')}"),
                        ("Result", "HEALTHY" if not problems else "; ".join(problems)),
                    ],
                )
            )
        return _finish(summary, results, "IPv6 address state failed on")
    except _ERRORS as exc:
        return runtime_exception(summary, exc)


def _global_addresses(iface, family: int) -> list[str]:
    kind = "inet6" if family == 6 else "inet"
    return [
        canonical_ip(entry.get("local"))
        for entry in iface.get("addr_info", [])
        if entry.get("family") == kind and entry.get("scope") == "global"
    ]


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
        extras = sorted({a for iface in located for a in _global_addresses(iface, family)})
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


def _nm_values(stdout: str) -> dict[str, str]:
    lines = [line.replace("\\:", ":").strip() for line in stdout.splitlines()]
    lines += [""] * (len(NM_PROFILE_FIELDS) - len(lines))
    return dict(zip(NM_PROFILE_FIELDS, lines))


def _nm_problems(mode, node, values) -> list[str]:
    problems = [
        f"{key}={values[key] or '<empty>'} (expected {expected})"
        for key, expected in NM_EXPECTED_METHODS[mode].items()
        if values[key] != expected
    ]
    if values["ipv6.ip6-privacy"] not in NM_PRIVACY_DISABLED:
        problems.append(f"ipv6.ip6-privacy={values['ipv6.ip6-privacy']}")
    problems.extend(
        f"{key}={values[key]}" for key in ("ipv4.gateway", "ipv6.gateway") if values[key]
    )
    configured = {
        (canonical_ip(address), prefix_length(address))
        for address in values["ipv6.addresses"].split(",")
        if address.strip()
    }
    if (node["ipv6"], node["prefix6"]) not in configured:
        problems.append(f"ipv6.addresses lacks {node['ipv6']}/{node['prefix6']}")
    return problems


def check_ipoib_ipv6_nm_profile(host) -> dict[str, Any]:
    """TC-FVT-002/009: NM profile methods, privacy, address, and no gateway."""
    summary = "IPoIB NetworkManager profile"
    try:
        mode, nodes, skip = _ipv6_selection(host, summary)
        if skip:
            return skip
        results = []
        for node in nodes:
            _iface, _info, name = _ib_iface(host, node)
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
            problems = _nm_problems(mode, node, values)
            results.append(
                (
                    node,
                    not problems,
                    [
                        ("Profile", name),
                        *[(key, values[key] or "<empty>") for key in NM_PROFILE_FIELDS],
                        ("Result", "matches" if not problems else "; ".join(problems)),
                    ],
                )
            )
        return _finish(summary, results, "NetworkManager profile mismatch on")
    except _ERRORS as exc:
        return runtime_exception(summary, exc)


def _route_problems(host, nodes, position, name):
    node = nodes[position]
    routes = remote_json(
        host, node["row"], IPOIB_COMMANDS["ipv6_routes_dev"] % shlex.quote(name)
    )
    defaults = remote_json(host, node["row"], IPOIB_COMMANDS["ipv6_default_routes"])
    problems = [
        f"route {route.get('dst')} via {route.get('gateway')}"
        for route in routes
        if route.get("dst") == "default" or route.get("gateway")
    ]
    problems.extend(f"default route on {name}" for route in defaults if route.get("dev") == name)
    details = [("Interface", name)]
    if len(nodes) > 1:
        peer = nodes[(position + 1) % len(nodes)]
        lookup = remote_json(
            host, node["row"], IPOIB_COMMANDS["ipv6_route_get"] % shlex.quote(peer["ipv6"])
        )
        entry = lookup[0] if isinstance(lookup, list) and lookup else {}
        details.append(
            ("Peer route", f"{peer['ipv6']} dev {entry.get('dev')} src {entry.get('prefsrc')}")
        )
        if entry.get("dev") != name or canonical_ip(entry.get("prefsrc")) != node["ipv6"]:
            problems.append("peer route does not use the IB interface and approved source")
    return problems, details


def check_ipoib_ipv6_routes(host) -> dict[str, Any]:
    """TC-FVT-009/015: no IPoIB default or gateway route; peers route via IB."""
    summary = "IPoIB IPv6 routing"
    try:
        _mode, nodes, skip = _ipv6_selection(host, summary)
        if skip:
            return skip
        results = []
        for position, node in enumerate(nodes):
            _iface, _info, name = _ib_iface(host, node)
            if not name:
                results.append((node, False, [("Routes", "IB interface not found")]))
                continue
            problems, details = _route_problems(host, nodes, position, name)
            details.append(("Result", "on-link only" if not problems else "; ".join(problems)))
            results.append((node, not problems, details))
        return _finish(summary, results, "IPoIB routing violation on")
    except _ERRORS as exc:
        return runtime_exception(summary, exc)


def check_ipoib_ipv6_peer_mesh(host) -> dict[str, Any]:
    """TC-FVT-023: each IB node reaches every peer over IPv6 (and IPv4 in dual-stack)."""
    summary = "IPoIB peer reachability"
    try:
        mode, nodes, skip = _ipv6_selection(host, summary, minimum=2)
        if skip:
            return skip
        families = (6, 4) if mode == IB_MODE_DUAL_STACK else (6,)
        results = []
        for source in nodes:
            _iface, _info, name = _ib_iface(host, source)
            unreachable = []
            for peer in nodes:
                if peer is source:
                    continue
                for family in families:
                    target = peer["ipv6"] if family == 6 else peer["ipv4"]
                    label = f"{peer['row']['HOSTNAME']} IPv{family}"
                    if not target or not name:
                        unreachable.append(label)
                        continue
                    probe = remote_command(
                        host,
                        source["row"],
                        IPOIB_COMMANDS["ping_from_iface"]
                        % (family, PING_TIMEOUT_SECONDS, shlex.quote(name), shlex.quote(target)),
                    )
                    if probe.rc != 0:
                        unreachable.append(label)
            details = [
                ("Interface", name or "missing"),
                ("Unreachable", ", ".join(unreachable) or "none"),
            ]
            results.append((source, not unreachable, details))
        return _finish(summary, results, "IPoIB peers unreachable from")
    except _ERRORS as exc:
        return runtime_exception(summary, exc)


def check_ipoib_ipv6_smd_records(host) -> dict[str, Any]:
    """TC-FVT-011: SMD holds every approved IPoIB address for each node."""
    summary = "IPoIB SMD publication"
    try:
        mode, nodes, skip = _ipv6_selection(host, summary)
        if skip:
            return skip
        published = {
            canonical_ip(address)
            for interface in resource_list(api_json(host, "ethernet"))
            for address in interface_ips(interface)
        }
        results = []
        for node in nodes:
            expected = [node["ipv6"]]
            if mode == IB_MODE_DUAL_STACK and node["ipv4"]:
                expected.append(node["ipv4"])
            missing = [address for address in expected if address not in published]
            results.append(
                (
                    node,
                    not missing,
                    [
                        ("Expected", ", ".join(expected)),
                        ("Missing in SMD", ", ".join(missing) or "none"),
                    ],
                )
            )
        return _finish(summary, results, "SMD is missing IPoIB addresses for")
    except _ERRORS as exc:
        return runtime_exception(summary, exc)


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
    family = 6 if mode in IPV6_MODES else 4
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
        family = 6 if mode in IPV6_MODES else 4
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
