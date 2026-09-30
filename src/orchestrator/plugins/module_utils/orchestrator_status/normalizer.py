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

"""Normalize and merge per-node Orchestrator lifecycle state."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .errors import StatusReconcileError


def mapping(value: Any) -> dict[str, Any]:
    """Return a defensive mapping copy or an empty mapping."""
    return deepcopy(value) if isinstance(value, dict) else {}


def mapping_list(value: Any, field: str) -> list[dict[str, Any]]:
    """Validate and copy a list of mappings."""
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise StatusReconcileError(f"{field} must be a list of dictionaries")
    return deepcopy(value)


def _required_xname(node: dict[str, Any], field: str) -> str:
    """Return a required normalized XNAME."""
    xname = str(node.get("xname", "")).strip()
    if not xname:
        raise StatusReconcileError(f"{field} contains a node without an XNAME")
    return xname


def _index_nodes(nodes: list[dict[str, Any]], field: str) -> dict[str, dict[str, Any]]:
    """Index nodes by unique XNAME."""
    indexed: dict[str, dict[str, Any]] = {}
    for node in nodes:
        xname = _required_xname(node, field)
        if xname in indexed:
            raise StatusReconcileError(f"{field} contains duplicate XNAME {xname}")
        indexed[xname] = node
    return indexed


def _provisioning_status(node: dict[str, Any]) -> str:
    """Return the normalized desired-state provisioning status."""
    provisioning = mapping(node.get("provisioning"))
    return str(
        node.get("provisioning_status", provisioning.get("status", "unknown"))
    )


def normalize_node(node: dict[str, Any]) -> dict[str, Any]:
    """Return the stable compact node status schema."""
    xname = _required_xname(node, "node status")
    pxeboot = mapping(node.get("pxeboot"))
    pxeboot_status = str(pxeboot.get("status", "not_run"))
    pxeboot_state = str(
        pxeboot.get(
            "state",
            pxeboot.get(
                "verification_state",
                "not_run" if pxeboot_status == "not_run" else pxeboot_status,
            ),
        )
    )
    reprovision_required = bool(node.get("reprovision_required", False))
    raw_status = str(node.get("status", ""))
    status = "failed" if raw_status == "failed" else (
        "pending" if reprovision_required else "success"
    )
    return {
        "xname": xname,
        "hostname": node.get("hostname", "N/A"),
        "admin_ip": node.get("admin_ip", "N/A"),
        "bmc_ip": node.get("bmc_ip", "N/A"),
        "status": status,
        "reprovision_required": reprovision_required,
        "provisioning_status": _provisioning_status(node),
        "pxeboot": {
            "status": pxeboot_status,
            "state": pxeboot_state,
            "trigger_method": pxeboot.get(
                "trigger_method",
                "not_run" if pxeboot_status == "not_run" else "orchestrator",
            ),
            "verification_method": pxeboot.get(
                "verification_method",
                "ssh_cloud_init" if pxeboot_status == "success" else "not_run",
            ),
        },
    }


def merge_nodes(
    previous_nodes: list[dict[str, Any]],
    current_nodes: list[dict[str, Any]],
    preserve_unselected: bool,
) -> list[dict[str, Any]]:
    """Merge a partial PXE result without losing unselected pending nodes."""
    current_by_xname = _index_nodes(current_nodes, "current_nodes")
    if not preserve_unselected:
        return current_nodes

    previous_by_xname = _index_nodes(previous_nodes, "previous_status.nodes")
    merged = [current_by_xname.get(xname, node) for xname, node in previous_by_xname.items()]
    merged.extend(
        node for xname, node in current_by_xname.items() if xname not in previous_by_xname
    )
    return merged


# The external path keeps the verification and lifecycle outcomes separate so
# a successful boot cannot overwrite an incomplete provisioning result.
# pylint: disable=too-many-locals
def external_current_nodes(
    previous_nodes: list[dict[str, Any]],
    selected_xnames: list[str],
    verification_results: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build node and failure data for externally booted nodes."""
    selected = [str(xname).strip() for xname in selected_xnames]
    if any(not xname for xname in selected) or len(set(selected)) != len(selected):
        raise StatusReconcileError("selected_xnames must contain unique, non-empty XNAMEs")

    previous_by_xname = _index_nodes(previous_nodes, "previous_status.nodes")
    results_by_xname = _index_nodes(verification_results, "verification_results")
    unknown = sorted(set(selected) - set(previous_by_xname))
    if unknown:
        raise StatusReconcileError(
            "selected_xnames are absent from previous_status.nodes: " + ", ".join(unknown)
        )

    current: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for xname in selected:
        previous = previous_by_xname[xname]
        result = results_by_xname.get(xname, {})
        provisioning_succeeded = _provisioning_status(previous) == "success"
        verification_succeeded = result.get("status") == "success"
        lifecycle_succeeded = provisioning_succeeded and verification_succeeded
        blocked_by_provisioning = not provisioning_succeeded
        state = (
            "blocked_by_provisioning"
            if blocked_by_provisioning
            else str(result.get("state", "verification_result_missing"))
        )
        current.append(
            {
                **previous,
                "status": "success" if lifecycle_succeeded else "failed",
                "reprovision_required": not lifecycle_succeeded,
                "pxeboot": {
                    "status": (
                        "not_run"
                        if blocked_by_provisioning
                        else ("success" if verification_succeeded else "failed")
                    ),
                    "state": (
                        state
                        if blocked_by_provisioning
                        else ("success" if verification_succeeded else state)
                    ),
                    "trigger_method": (
                        "not_run" if blocked_by_provisioning else "external"
                    ),
                    "verification_method": (
                        "not_started"
                        if blocked_by_provisioning
                        else "ssh_cloud_init"
                    ),
                },
            }
        )
        if not lifecycle_succeeded:
            failures.append(
                {
                    "xname": xname,
                    "hostname": previous.get("hostname", ""),
                    "admin_ip": previous.get("admin_ip", ""),
                    "bmc_ip": previous.get("bmc_ip", ""),
                    "failure_stage": (
                        "provisioning"
                        if blocked_by_provisioning
                        else "node_registration"
                    ),
                    "verification_state": state,
                    "trigger_method": (
                        "not_run" if blocked_by_provisioning else "external"
                    ),
                    "verification_method": (
                        "not_started"
                        if blocked_by_provisioning
                        else "ssh_cloud_init"
                    ),
                    "status": "failed",
                }
            )
    return current, failures


def count_status(nodes: list[dict[str, Any]], status: str) -> int:
    """Count nodes with one lifecycle status."""
    return sum(node.get("status") == status for node in nodes)
