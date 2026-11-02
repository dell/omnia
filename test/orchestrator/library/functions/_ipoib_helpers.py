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

"""Private address, mode, and output-parsing helpers for IPoIB checks."""

import ipaddress
import json
from collections.abc import Mapping
from typing import Any

from ..vars.ipoib_vars import (
    IB_MODE_IPV4_ONLY,
    IB_NETWORK_KEY,
    LEGACY_IB_COLUMN,
    VALIDATION_ERROR_LABELS,
    VALIDATION_ERROR_LINE,
)


def ib_network_block(network_spec: Mapping[str, Any]) -> dict[str, Any]:
    """Return the ib_network mapping from a parsed network_spec.yml."""
    networks = network_spec.get("Networks")
    if not isinstance(networks, list):
        raise TypeError("network_spec.yml Networks must be a list")
    for entry in networks:
        if isinstance(entry, dict) and isinstance(entry.get(IB_NETWORK_KEY), dict):
            return entry[IB_NETWORK_KEY]
    raise ValueError("network_spec.yml has no ib_network entry")


def ib_addr_mode(block: Mapping[str, Any]) -> str:
    """Return the effective IPoIB mode; the product default is ipv4-only."""
    return str(block.get("ib_addr_mode") or IB_MODE_IPV4_ONLY).strip()


def ib_subnet(block: Mapping[str, Any], family: int):
    """Return the configured IB network for one family, or None when unset."""
    if family == 6:
        subnet, bits = block.get("ipv6_subnet"), block.get("ipv6_netmask_bits")
    else:
        subnet = block.get("ipv4_subnet", block.get("subnet"))
        bits = block.get("ipv4_netmask_bits", block.get("netmask_bits"))
    subnet, bits = str(subnet or "").strip(), str(bits or "").strip()
    if not subnet or not bits:
        return None
    network = ipaddress.ip_network(f"{subnet}/{bits}", strict=False)
    if network.version != family:
        raise ValueError(
            f"ib_network IPv{family} subnet {subnet} has the wrong address family"
        )
    return network


def canonical_ip(value: object) -> str:
    """Return the canonical address without prefix, or an empty string."""
    text = str(value or "").strip().split("/", 1)[0]
    try:
        return str(ipaddress.ip_address(text)) if text else ""
    except ValueError:
        return ""


def prefix_length(value: object) -> int | None:
    """Return an explicit '/N' prefix from an address cell, if present."""
    text = str(value or "").strip()
    if "/" not in text:
        return None
    try:
        return int(text.split("/", 1)[1])
    except ValueError:
        return None


def row_address(row: Mapping[str, str], family: int) -> str:
    """Return a row's raw IB address for one family, honouring legacy IB_IP."""
    column = "IB_IPV6" if family == 6 else "IB_IPV4"
    for value in (row.get(column), row.get(LEGACY_IB_COLUMN)):
        address = canonical_ip(value)
        if address and ipaddress.ip_address(address).version == family:
            return str(value).strip()
    return ""


def validation_errors(output: str) -> set[str]:
    """Extract individual product validation errors from playbook output."""
    errors = set()
    for line in output.splitlines():
        match = VALIDATION_ERROR_LINE.match(line)
        if not match:
            continue
        try:
            message = json.loads(match.group("message"))
        except json.JSONDecodeError:
            continue
        if isinstance(message, str) and message.startswith(VALIDATION_ERROR_LABELS):
            errors.add(message.strip())
    return errors
