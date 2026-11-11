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

"""Build compact, persistent Orchestrator PXE lifecycle reports."""

# The public function mirrors the Ansible module contract. Keeping that
# boundary explicit avoids an untyped options dictionary in the core logic.
# pylint: disable=too-many-arguments,too-many-locals

from __future__ import annotations

from typing import Any

from .errors import StatusReconcileError
from .normalizer import (
    count_status,
    external_current_nodes,
    mapping,
    mapping_list,
    merge_nodes,
    normalize_node,
)

SCHEMA_VERSION = "1.0"


def _provisioning_phase(report: dict[str, Any]) -> dict[str, Any]:
    """Return the stable provisioning phase summary."""
    if not report:
        return {
            "status": "not_run",
            "total_nodes": 0,
            "success_count": 0,
            "failure_count": 0,
            "timestamp": "",
            "report": "provisioning_report.yml",
        }
    missing = report.get("missing_nodes", [])
    if not isinstance(missing, list):
        raise StatusReconcileError("provisioning_report.missing_nodes must be a list")
    total = int(report.get("total_expected_nodes", 0))
    return {
        "status": "failed" if missing else "success",
        "total_nodes": total,
        "success_count": max(total - len(missing), 0),
        "failure_count": len(missing),
        "timestamp": report.get("timestamp", ""),
        "report": "provisioning_report.yml",
    }


def reconcile_pxeboot_status(
    *,
    previous_status: Any,
    current_nodes: Any,
    failed_nodes: Any,
    inventory_source: str,
    timestamp: str,
    run_id: str,
    verification_enabled: bool,
    custom_inventory: bool,
    preserve_unselected: bool,
    unverified_count: int,
    provisioning_report: Any = None,
    selected_xnames: Any = None,
    verification_results: Any = None,
) -> dict[str, Any]:
    """Return canonical aggregate and failed-node PXE reports."""
    previous = mapping(previous_status)
    previous_nodes = mapping_list(previous.get("nodes", []), "previous_status.nodes")
    requested_xnames = selected_xnames or []
    external_mode = bool(requested_xnames or verification_results is not None)

    if external_mode:
        if not isinstance(requested_xnames, list):
            raise StatusReconcileError("selected_xnames must be a list")
        results = mapping_list(verification_results or [], "verification_results")
        phase_nodes, failures = external_current_nodes(
            previous_nodes, requested_xnames, results
        )
        aggregate_nodes = merge_nodes(previous_nodes, phase_nodes, True)
    else:
        phase_nodes = mapping_list(current_nodes, "current_nodes")
        failures = mapping_list(failed_nodes, "failed_nodes")
        aggregate_nodes = merge_nodes(
            previous_nodes, phase_nodes, bool(preserve_unselected)
        )

    compact_nodes = [normalize_node(node) for node in aggregate_nodes]
    aggregate_failure_count = count_status(compact_nodes, "failed")
    aggregate_success_count = count_status(compact_nodes, "success")
    phase_failure_count = len(failures)
    phase_total = len(phase_nodes)
    phase_success_count = max(phase_total - phase_failure_count, 0)
    previous_phases = mapping(previous.get("phases"))
    provisioning = _provisioning_phase(mapping(provisioning_report))
    if not provisioning_report:
        provisioning = mapping(previous_phases.get("provisioning")) or provisioning

    failed_report = {
        "schema_version": SCHEMA_VERSION,
        "phase": "pxeboot",
        "run_id": str(run_id),
        "timestamp": timestamp,
        "total_nodes": phase_total,
        "success_count": phase_success_count,
        "failure_count": phase_failure_count,
        "verification_enabled": bool(verification_enabled),
        "unverified_count": int(unverified_count),
        "inventory_source": inventory_source,
        "failed_nodes": failures,
    }

    status_report = {
        **previous,
        "schema_version": SCHEMA_VERSION,
        "run_id": str(run_id),
        "overall_status": (
            "failed"
            if aggregate_failure_count
            or provisioning.get("failure_count", 0)
            else "success"
        ),
        "last_completed_phase": "pxeboot",
        "timestamp": timestamp,
        "total_nodes": len(compact_nodes),
        "success_count": aggregate_success_count,
        "failure_count": aggregate_failure_count,
        "verification_enabled": bool(verification_enabled),
        "unverified_count": (
            int(unverified_count)
            if external_mode
            else sum(
                node["pxeboot"]["state"] == "unverified" for node in compact_nodes
            )
        ),
        "custom_inventory": bool(custom_inventory),
        "nodes": compact_nodes,
        "inventory_source": inventory_source,
        "phases": {
            **previous_phases,
            "provisioning": provisioning,
            "pxeboot": {
                "status": "failed" if phase_failure_count else "success",
                "total_nodes": phase_total,
                "success_count": phase_success_count,
                "failure_count": phase_failure_count,
                "unverified_count": int(unverified_count),
                "timestamp": timestamp,
            },
        },
        "artifacts": {
            **mapping(previous.get("artifacts")),
            "provisioning_report": "provisioning_report.yml",
            "failed_nodes": "failed_nodes.json",
        },
    }
    return {
        "orchestrator_status": status_report,
        "failed_nodes_report": failed_report,
        "failed_xnames": [str(node.get("xname", "")) for node in failures],
    }
