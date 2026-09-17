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
"""Shared, side-effect-free helpers for OpenCHAMI SMD modules."""

from __future__ import annotations

from typing import Any


def normalize_mac(value: Any) -> str:
    """Return a canonical lowercase, colon-separated MAC address."""
    compact = str(value or "").strip().lower().replace("-", ":")
    if ":" not in compact and len(compact) == 12:
        compact = ":".join(
            compact[index:index + 2] for index in range(0, 12, 2)
        )
    return compact


def interface_ips(interface: dict[str, Any]) -> set[str]:
    """Return all IP addresses declared by an SMD EthernetInterface."""
    addresses = set()
    for entry in interface.get("IPAddresses") or []:
        value = entry.get("IPAddress", "") if isinstance(entry, dict) else entry
        value = str(value or "").strip()
        if value:
            addresses.add(value)
    return addresses


def is_node_interface(interface: dict[str, Any]) -> bool:
    """Accept Node interfaces and legacy responses that omit ``Type``."""
    interface_type = str(interface.get("Type", "") or "").strip().lower()
    return interface_type in {"", "node"}


def response_records(response: Any, key: str) -> tuple[list[dict[str, Any]], str]:
    """Normalize a list or keyed API response and report an invalid shape."""
    records = response
    if isinstance(response, dict):
        if key not in response:
            return [], f"API response is missing the '{key}' list"
        records = response[key]
    if not isinstance(records, list):
        return [], f"API response field '{key}' must be a list"
    if any(not isinstance(record, dict) for record in records):
        return [], f"API response field '{key}' contains a non-object record"
    return records, ""
