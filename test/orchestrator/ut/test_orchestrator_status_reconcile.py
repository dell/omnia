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

"""Regression contracts for Orchestrator lifecycle status reconciliation."""

# The src plugin root must be added before importing the collection helpers.
# pylint: disable=wrong-import-position

import sys
from pathlib import Path

import pytest

_SRC_PLUGIN_ROOT = str(
    Path(__file__).resolve().parents[3] / "src" / "orchestrator" / "plugins"
)
if _SRC_PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, _SRC_PLUGIN_ROOT)

try:
    from module_utils.orchestrator_status import (
        StatusReconcileError,
        reconcile_pxeboot_status,
    )
    from module_utils.orchestrator_status.normalizer import external_current_nodes
except ModuleNotFoundError as error:
    pytest.skip(
        f"Orchestrator lifecycle reconciliation module is unavailable: {error}",
        allow_module_level=True,
    )


def _node(
    xname: str = "x1000c0s0b0n0",
    *,
    provisioning_status: str = "success",
    status: str = "pending",
    reprovision_required: bool = True,
) -> dict:
    """Return one compact persisted lifecycle node."""
    return {
        "xname": xname,
        "hostname": "nid001",
        "admin_ip": "192.0.2.10",
        "bmc_ip": "192.0.2.20",
        "status": status,
        "reprovision_required": reprovision_required,
        "provisioning_status": provisioning_status,
        "pxeboot": {
            "status": "failed",
            "state": "idrac_unreachable",
            "trigger_method": "orchestrator",
            "verification_method": "not_started",
        },
    }


def _previous(node: dict, *, provisioning_failure_count: int = 0) -> dict:
    """Return aggregate status containing one previous node."""
    return {
        "schema_version": "1.0",
        "nodes": [node],
        "phases": {
            "provisioning": {
                "status": "failed" if provisioning_failure_count else "success",
                "total_nodes": 1,
                "success_count": 1 - provisioning_failure_count,
                "failure_count": provisioning_failure_count,
                "timestamp": "2026-09-30T00:00:00Z",
                "report": "provisioning_report.yml",
            }
        },
    }


def _reconcile(previous: dict, result: dict) -> dict:
    """Reconcile one external verification result."""
    return reconcile_pxeboot_status(
        previous_status=previous,
        current_nodes=[],
        failed_nodes=[],
        inventory_source="/opt/omnia/mapping.csv",
        timestamp="2026-09-30T00:01:00Z",
        run_id="test-run",
        verification_enabled=True,
        custom_inventory=False,
        preserve_unselected=True,
        unverified_count=0,
        selected_xnames=["x1000c0s0b0n0"],
        verification_results=[result],
    )


def _reconcile_managed(
    *,
    previous: dict | None = None,
    current_nodes: list[dict] | None = None,
    failed_nodes: list[dict] | None = None,
    preserve_unselected: bool = False,
) -> dict:
    """Reconcile one platform-managed PXE result."""
    return reconcile_pxeboot_status(
        previous_status=previous or {},
        current_nodes=current_nodes or [],
        failed_nodes=failed_nodes or [],
        inventory_source="/opt/omnia/mapping.csv",
        timestamp="2026-09-30T00:01:00Z",
        run_id="test-run",
        verification_enabled=True,
        custom_inventory=False,
        preserve_unselected=preserve_unselected,
        unverified_count=0,
        provisioning_report={
            "total_expected_nodes": len(current_nodes or []),
            "missing_nodes": [],
            "timestamp": "2026-09-30T00:00:00Z",
        },
    )


def test_external_success_clears_pending_after_successful_provisioning():
    """External verification completes a fully provisioned node lifecycle."""
    result = _reconcile(
        _previous(_node()),
        {"xname": "x1000c0s0b0n0", "status": "success", "state": "success"},
    )

    status = result["orchestrator_status"]
    node = status["nodes"][0]
    assert status["overall_status"] == "success"
    assert node["status"] == "success"
    assert node["reprovision_required"] is False
    assert node["pxeboot"] == {
        "status": "success",
        "state": "success",
        "trigger_method": "external",
        "verification_method": "ssh_cloud_init",
    }
    assert result["failed_xnames"] == []


def test_external_success_cannot_override_failed_provisioning():
    """A verified boot cannot publish success for incomplete desired state."""
    result = _reconcile(
        _previous(
            _node(provisioning_status="failed", status="failed"),
            provisioning_failure_count=1,
        ),
        {"xname": "x1000c0s0b0n0", "status": "success", "state": "success"},
    )

    status = result["orchestrator_status"]
    node = status["nodes"][0]
    assert status["overall_status"] == "failed"
    assert status["phases"]["provisioning"]["status"] == "failed"
    assert node["status"] == "failed"
    assert node["provisioning_status"] == "failed"
    assert node["reprovision_required"] is True
    assert node["pxeboot"] == {
        "status": "not_run",
        "state": "blocked_by_provisioning",
        "trigger_method": "not_run",
        "verification_method": "not_started",
    }
    assert result["failed_xnames"] == ["x1000c0s0b0n0"]
    assert result["failed_nodes_report"]["failed_nodes"][0][
        "failure_stage"
    ] == "provisioning"


def test_external_overall_status_retains_provisioning_phase_failure():
    """A retained provisioning-phase failure always keeps aggregate failure."""
    result = _reconcile(
        _previous(_node(), provisioning_failure_count=1),
        {"xname": "x1000c0s0b0n0", "status": "success", "state": "success"},
    )

    status = result["orchestrator_status"]
    assert status["nodes"][0]["status"] == "success"
    assert status["phases"]["provisioning"]["failure_count"] == 1
    assert status["overall_status"] == "failed"


@pytest.mark.parametrize("provisioning_status", ["unknown", ""])
def test_external_success_fails_closed_without_successful_provisioning(
    provisioning_status,
):
    """Unknown or empty provisioning state cannot clear pending state."""
    current, failures = external_current_nodes(
        [_node(provisioning_status=provisioning_status, status="failed")],
        ["x1000c0s0b0n0"],
        [{"xname": "x1000c0s0b0n0", "status": "success", "state": "success"}],
    )

    assert current[0]["status"] == "failed"
    assert current[0]["reprovision_required"] is True
    assert current[0]["pxeboot"]["state"] == "blocked_by_provisioning"
    assert failures[0]["failure_stage"] == "provisioning"


def test_external_failure_preserves_pending_after_successful_provisioning():
    """SSH or cloud-init failure keeps an otherwise provisioned node pending."""
    result = _reconcile(
        _previous(_node()),
        {
            "xname": "x1000c0s0b0n0",
            "status": "failed",
            "state": "cloud_init_error",
        },
    )

    node = result["orchestrator_status"]["nodes"][0]
    assert result["orchestrator_status"]["overall_status"] == "failed"
    assert node["status"] == "failed"
    assert node["reprovision_required"] is True
    assert node["pxeboot"]["state"] == "cloud_init_error"
    assert result["failed_xnames"] == ["x1000c0s0b0n0"]


def test_external_subset_preserves_unselected_failure():
    """A successful subset result cannot erase another failed node."""
    selected = _node()
    unselected = _node(
        "x1000c0s0b0n1",
        provisioning_status="failed",
        status="failed",
    )
    previous = _previous(selected, provisioning_failure_count=1)
    previous["nodes"].append(unselected)

    result = _reconcile(
        previous,
        {"xname": "x1000c0s0b0n0", "status": "success", "state": "success"},
    )

    nodes = {
        node["xname"]: node for node in result["orchestrator_status"]["nodes"]
    }
    assert result["orchestrator_status"]["overall_status"] == "failed"
    assert nodes["x1000c0s0b0n0"]["status"] == "success"
    assert nodes["x1000c0s0b0n1"]["status"] == "failed"
    assert nodes["x1000c0s0b0n1"]["reprovision_required"] is True


def test_external_results_reject_duplicate_xnames():
    """Ambiguous external results fail before lifecycle state is changed."""
    with pytest.raises(StatusReconcileError, match="duplicate XNAME"):
        external_current_nodes(
            [_node()],
            ["x1000c0s0b0n0"],
            [
                {"xname": "x1000c0s0b0n0", "status": "success"},
                {"xname": "x1000c0s0b0n0", "status": "success"},
            ],
        )


def test_managed_pxeboot_success_produces_canonical_outputs():
    """Managed PXE success populates both stable output contracts."""
    node = _node(status="success", reprovision_required=False)
    node["pxeboot"] = {
        "status": "success",
        "state": "success",
        "trigger_method": "orchestrator",
        "verification_method": "ssh_cloud_init",
    }

    result = _reconcile_managed(current_nodes=[node])

    status = result["orchestrator_status"]
    failed = result["failed_nodes_report"]
    assert status["schema_version"] == "1.0"
    assert status["overall_status"] == "success"
    assert status["last_completed_phase"] == "pxeboot"
    assert (status["total_nodes"], status["success_count"], status["failure_count"]) == (
        1,
        1,
        0,
    )
    assert status["phases"]["provisioning"]["status"] == "success"
    assert status["phases"]["pxeboot"] == {
        "status": "success",
        "total_nodes": 1,
        "success_count": 1,
        "failure_count": 0,
        "unverified_count": 0,
        "timestamp": "2026-09-30T00:01:00Z",
    }
    assert status["artifacts"] == {
        "provisioning_report": "provisioning_report.yml",
        "failed_nodes": "failed_nodes.json",
    }
    assert failed["schema_version"] == "1.0"
    assert failed["phase"] == "pxeboot"
    assert (failed["total_nodes"], failed["success_count"], failed["failure_count"]) == (
        1,
        1,
        0,
    )
    assert failed["failed_nodes"] == []
    assert result["failed_xnames"] == []


def test_managed_pxeboot_failure_is_preserved_in_both_outputs():
    """Managed PXE failure remains pending and appears in failed-node output."""
    node = _node(status="failed", reprovision_required=True)
    failure = {
        "xname": node["xname"],
        "hostname": node["hostname"],
        "admin_ip": node["admin_ip"],
        "bmc_ip": node["bmc_ip"],
        "failure_stage": "node_registration",
        "verification_state": "cloud_init_error",
        "status": "failed",
    }

    result = _reconcile_managed(current_nodes=[node], failed_nodes=[failure])

    status = result["orchestrator_status"]
    assert status["overall_status"] == "failed"
    assert status["nodes"][0]["status"] == "failed"
    assert status["nodes"][0]["reprovision_required"] is True
    assert status["phases"]["pxeboot"]["failure_count"] == 1
    assert result["failed_nodes_report"]["failed_nodes"] == [failure]
    assert result["failed_xnames"] == [node["xname"]]


def test_managed_partial_retry_preserves_unselected_node_history():
    """A managed one-node retry cannot erase an untouched failed node."""
    retried = _node(status="pending", reprovision_required=True)
    untouched = _node(
        "x1000c0s0b0n1",
        provisioning_status="success",
        status="failed",
        reprovision_required=True,
    )
    previous = _previous(retried)
    previous["nodes"].append(untouched)
    retried["status"] = "success"
    retried["reprovision_required"] = False
    retried["pxeboot"] = {
        "status": "success",
        "state": "success",
        "trigger_method": "orchestrator",
        "verification_method": "ssh_cloud_init",
    }

    result = _reconcile_managed(
        previous=previous,
        current_nodes=[retried],
        preserve_unselected=True,
    )

    nodes = {
        node["xname"]: node for node in result["orchestrator_status"]["nodes"]
    }
    assert result["orchestrator_status"]["overall_status"] == "failed"
    assert nodes["x1000c0s0b0n0"]["status"] == "success"
    assert nodes["x1000c0s0b0n1"]["status"] == "failed"
    assert nodes["x1000c0s0b0n1"]["reprovision_required"] is True
