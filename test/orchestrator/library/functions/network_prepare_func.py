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

"""Network postcondition helpers for the prepare lifecycle."""

import ipaddress
import posixpath
from collections.abc import Mapping
from typing import Any

from omnia_auto import run_on_host

from ..vars.prepare_vars import (
    DEFAULT_DNS_FORWARDERS,
    FIREWALL_PORTS,
    PODMAN_TRUSTED_INTERFACES,
    PREPARE_COMMANDS,
)
from ._prepare_helpers import prepare_result, read_yaml_mapping
from .project_func import resolve_target_input_project_path


def check_prepare_firewall_network(host) -> dict[str, Any]:
    """Verify firewall ports, trusted interfaces and masquerade policy."""
    fields = []
    failures = []

    firewalld = run_on_host(host, PREPARE_COMMANDS["unit_active"], "firewalld.service")
    firewalld_state = firewalld.stdout.strip() if firewalld.rc == 0 else "inactive"
    fields.append(("firewalld.service", firewalld_state))
    if firewalld_state != "active":
        failures.append("firewalld.service")

    for port in FIREWALL_PORTS:
        probe = run_on_host(host, PREPARE_COMMANDS["firewall_port"], port)
        state = "open" if probe.rc == 0 else "closed"
        fields.append((f"Firewall {port}", state))
        if probe.rc != 0:
            failures.append(port)

    for interface in PODMAN_TRUSTED_INTERFACES:
        probe = run_on_host(host, PREPARE_COMMANDS["firewall_interface"], interface)
        state = "trusted" if probe.rc == 0 else "not trusted"
        fields.append((f"Interface {interface}", state))
        if probe.rc != 0:
            failures.append(interface)

    masquerade = run_on_host(host, PREPARE_COMMANDS["firewall_masquerade"])
    masquerade_disabled = masquerade.stdout.strip().lower() == "no"
    fields.append(
        (
            "Trusted-zone masquerading",
            "disabled" if masquerade_disabled else "enabled",
        )
    )
    if not masquerade_disabled:
        failures.append("trusted-zone masquerading")

    return prepare_result(
        not failures,
        "Orchestrator firewall and Podman trust policy checked",
        fields,
        "Invalid network policy: " + ", ".join(failures) if failures else "",
    )


def _admin_network(host) -> Mapping[str, Any]:
    """Return the normalized admin network mapping from network_spec.yml."""
    path = posixpath.join(resolve_target_input_project_path(host), "network_spec.yml")
    spec = read_yaml_mapping(host, path)
    networks = spec.get("Networks", spec.get("networks", []))
    if not isinstance(networks, list):
        raise TypeError("network_spec.yml Networks must be a list")
    for network in networks:
        if isinstance(network, dict) and isinstance(network.get("admin_network"), dict):
            return network["admin_network"]
    raise ValueError("network_spec.yml does not define admin_network")


def check_prepare_coredhcp_network(host) -> dict[str, Any]:
    """Compare rendered CoreDHCP/CoreDNS configuration with network_spec."""
    try:
        admin = _admin_network(host)
        coredhcp = host.file("/etc/openchami/configs/coredhcp.yaml").content_string
        corefile = host.file("/etc/openchami/configs/Corefile").content_string
        admin_ip = str(admin["primary_oim_admin_ip"])
        prefix = int(admin["netmask_bits"])
        router = str(admin["router"])
        dynamic_range = str(admin["dynamic_range"])
        range_start, range_end = dynamic_range.split("-", 1)
        primary_network = ipaddress.ip_network(f"{admin_ip}/{prefix}", strict=False)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        return prepare_result(
            False, "Unable to build network expectations", [], str(exc)
        )

    fields = []
    failures = []
    required_primary = {
        "CoreDHCP server ID": f"server_id: {admin_ip}",
        "CoreDHCP router": f"router: {router}",
        "Primary DHCP pool": (
            f"subnet_pool={primary_network},{range_start},{range_end}"
        ),
        "CoreDNS bind": f"bind {admin_ip}",
    }
    for label, expected in required_primary.items():
        source = corefile if label == "CoreDNS bind" else coredhcp
        matched = expected in source
        fields.append((label, "matched" if matched else "missing"))
        if not matched:
            failures.append(label)

    configured_dns = admin.get("dns", []) or list(DEFAULT_DNS_FORWARDERS)
    dns_line = "forward . " + " ".join(str(item) for item in configured_dns)
    dns_matched = dns_line in corefile
    fields.append(("CoreDNS forwarders", "matched" if dns_matched else "missing"))
    if not dns_matched:
        failures.append("CoreDNS forwarders")

    additional = admin.get("additional_subnets", []) or []
    if not isinstance(additional, list):
        return prepare_result(
            False,
            "Invalid additional_subnets contract",
            fields,
            "admin_network.additional_subnets must be a list",
        )
    for subnet in additional:
        try:
            cidr = f"{subnet['subnet']}/{int(subnet['netmask_bits'])}"
            start, end = str(subnet["dynamic_range"]).split("-", 1)
            subnet_router = str(subnet["router"])
        except (KeyError, TypeError, ValueError) as exc:
            failures.append(f"invalid additional subnet: {exc}")
            continue
        expected_lines = (
            f"rule=subnet:{cidr},type:Node,routers:{subnet_router}",
            f"rule=subnet:{cidr},type:NodeBMC,routers:{subnet_router}",
            f"subnet_pool={cidr},{start},{end}",
        )
        config_ok = all(line in coredhcp for line in expected_lines)
        route = run_on_host(host, PREPARE_COMMANDS["route"], cidr)
        route_ok = route.rc == 0 and bool(route.stdout.strip())
        fields.extend(
            [
                (
                    f"CoreDHCP subnet {cidr}",
                    "matched" if config_ok else "missing",
                ),
                (f"Route {cidr}", "present" if route_ok else "missing"),
            ]
        )
        if not config_ok:
            failures.append(f"CoreDHCP subnet {cidr}")
        if not route_ok:
            failures.append(f"route {cidr}")

    fields.append(("Additional subnets", len(additional)))
    return prepare_result(
        not failures,
        "CoreDHCP, CoreDNS and additional-subnet routes checked",
        fields,
        "; ".join(failures),
    )
