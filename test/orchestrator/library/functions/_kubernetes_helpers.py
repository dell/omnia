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

"""Shared pure Kubernetes response helpers."""

from collections.abc import Mapping
from typing import Any


def pod_ready(item: Mapping[str, Any]) -> bool:
    """Return whether a Kubernetes pod reports all containers ready."""
    status = item.get("status", {})
    containers = status.get("containerStatuses") or []
    return (
        status.get("phase") == "Running"
        and bool(containers)
        and all(bool(entry.get("ready")) for entry in containers)
    )


def resolve_kubernetes_node(
    items: list[Any],
    hostname: str,
    admin_ip: str,
) -> tuple[str, Mapping[str, Any] | None]:
    """Resolve one desired node by Kubernetes name or InternalIP."""
    matches: dict[str, Mapping[str, Any]] = {}
    for item in items:
        if not isinstance(item, Mapping):
            continue
        metadata = item.get("metadata", {})
        status = item.get("status", {})
        name = str(metadata.get("name") or "")
        addresses = status.get("addresses", [])
        internal_ips = {
            str(address.get("address") or "")
            for address in addresses
            if isinstance(address, Mapping) and address.get("type") == "InternalIP"
        }
        if name == hostname or admin_ip in internal_ips:
            matches[name] = item
    if len(matches) > 1:
        raise ValueError(f"Multiple Kubernetes nodes resolve to {hostname}/{admin_ip}")
    if not matches:
        return "", None
    return next(iter(matches.items()))
