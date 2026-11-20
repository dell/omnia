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

"""Unit tests for ER-ORCH-009 lifecycle mutation safety and planning.

Covers:
  - TC_UT_planner_007: Exact-target add/remove planner (FR-4.1, FR-4.2, AC-005, AC-006)
  - TC_UT_lock_journal_008: Lock and recovery decisions (FR-5.1)
"""

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
ORCHESTRATOR_ROOT = REPO_ROOT / "src" / "orchestrator"
SOURCE_PLUGIN_ROOT = ORCHESTRATOR_ROOT / "plugins"
if str(SOURCE_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_PLUGIN_ROOT))


def _load_source_module(name, relative_path):
    path = ORCHESTRATOR_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


lifecycle = _load_source_module(
    "functional_group_lifecycle",
    "plugins/module_utils/functional_group_lifecycle.py",
)

LifecyclePlanner = lifecycle.LifecyclePlanner
ProjectLock = lifecycle.ProjectLock
TransitionJournal = lifecycle.TransitionJournal
BoundedRecoveryManager = lifecycle.BoundedRecoveryManager
LockContentionError = lifecycle.LockContentionError
NodeNotEmptiedError = lifecycle.NodeNotEmptiedError
OwnershipAmbiguityError = lifecycle.OwnershipAmbiguityError
RecoveryRequiredError = lifecycle.RecoveryRequiredError
LockStatus = lifecycle.LockStatus
TerminalResult = lifecycle.TerminalResult
StageName = lifecycle.StageName


# ==============================================================================
# TC_UT_planner_007: Exact-target add/remove planner
# ==============================================================================


def test_planner_builds_ordered_add_plan():
    """Verify exact-target add emits ordered smd_group -> bss -> metadata stages."""
    target = "fg_compute_rhel_10_2_x86_64"
    plan = LifecyclePlanner.plan_add(target_group=target, effective_config={})

    assert plan["operation"] == "add"
    assert plan["target_group"] == target
    assert plan["planned_stages"] == [
        StageName.SMD_GROUP.value,
        StageName.BSS.value,
        StageName.METADATA.value,
    ]
    assert plan["is_noop"] is False
    assert plan["stages_to_execute"] == plan["planned_stages"]


def test_planner_add_detects_noop_when_state_matches():
    """Verify add detects no-op when current state already matches desired state."""
    target = "fg_compute_rhel_10_2_x86_64"
    current_state = {
        "smd_group_present": True,
        "bss_config_matching": True,
        "metadata_matching": True,
    }
    plan = LifecyclePlanner.plan_add(
        target_group=target,
        effective_config={},
        current_state=current_state,
    )

    assert plan["operation"] == "add"
    assert plan["is_noop"] is True
    assert plan["stages_to_execute"] == []
    assert "already present" in plan["reason"]


def test_planner_remove_rejects_when_nodes_are_still_mapped():
    """AC-006: Verify removal is rejected when nodes remain mapped to the group."""
    target = "fg_compute_rhel_10_2_x86_64"
    mapped_nodes = ["node-001", "node-002", "node-003"]

    with pytest.raises(NodeNotEmptiedError) as exc_info:
        LifecyclePlanner.plan_remove(
            target_group=target,
            mapped_nodes=mapped_nodes,
        )

    error = exc_info.value
    assert error.group_name == target
    assert error.remaining_node_count == 3
    assert "3 node(s) are still mapped" in str(error)
    assert target in str(error)


def test_planner_remove_succeeds_when_group_is_empty():
    """Verify removal succeeds with metadata -> bss -> smd_group when 0 nodes mapped."""
    target = "fg_compute_rhel_10_2_x86_64"
    all_groups = [
        {"name": "fg_compute_rhel_10_2_x86_64", "nodes": []},
        {"name": "fg_storage_rhel_10_2_x86_64", "nodes": ["node-010"]},
        {"name": "slurm_compute_rhel_10_2_x86_64", "nodes": ["node-020"]},
    ]

    plan = LifecyclePlanner.plan_remove(
        target_group=target,
        mapped_nodes=[],
        all_functional_groups=all_groups,
        ownership_evidence={"owned": True, "ambiguous": False},
    )

    assert plan["operation"] == "remove"
    assert plan["target_group"] == target
    assert plan["planned_stages"] == [
        StageName.METADATA.value,
        StageName.BSS.value,
        StageName.SMD_GROUP.value,
    ]
    assert plan["is_noop"] is False
    # Verify shared service recalculation retains remaining flexible groups only
    remaining_names = [g["name"] for g in plan["remaining_groups"]]
    assert remaining_names == ["fg_storage_rhel_10_2_x86_64"]
    assert "slurm_compute_rhel_10_2_x86_64" not in remaining_names


def test_planner_remove_rejects_ambiguous_ownership():
    """Verify removal fails closed when ownership cannot be proven."""
    target = "fg_compute_rhel_10_2_x86_64"

    with pytest.raises(OwnershipAmbiguityError) as exc_info:
        LifecyclePlanner.plan_remove(
            target_group=target,
            mapped_nodes=[],
            ownership_evidence={"owned": False, "ambiguous": True, "reason": "No project label"},
        )

    assert target in str(exc_info.value)
    assert "ownership evidence is missing or ambiguous" in str(exc_info.value)


def test_planner_remove_fails_closed_when_ownership_missing():
    """Verify removal fails closed when ownership evidence is omitted/empty."""
    target = "fg_compute_rhel_10_2_x86_64"

    with pytest.raises(OwnershipAmbiguityError) as exc_info:
        LifecyclePlanner.plan_remove(
            target_group=target,
            mapped_nodes=[],
            ownership_evidence={},
        )

    assert target in str(exc_info.value)
    assert "ownership evidence is missing or ambiguous" in str(exc_info.value)


def test_planner_remove_detects_noop_when_records_already_absent():
    """Verify removal detects no-op when no SMD/BSS/metadata records exist."""
    target = "fg_compute_rhel_10_2_x86_64"
    current_state = {
        "smd_group_present": False,
        "bss_present": False,
        "metadata_present": False,
    }
    plan = LifecyclePlanner.plan_remove(
        target_group=target,
        mapped_nodes=[],
        current_state=current_state,
    )

    assert plan["is_noop"] is True
    assert plan["stages_to_execute"] == []
    assert "no existing SMD, BSS, or metadata records" in plan["reason"]


def test_planner_configure_scopes():
    """Verify configure-only plans for boot, cloud_init, and both scopes."""
    target = "fg_web_rhel_10_2_x86_64"

    plan_boot = LifecyclePlanner.plan_configure(target, configure_scope="boot")
    assert plan_boot["planned_stages"] == [StageName.BSS.value]

    plan_ci = LifecyclePlanner.plan_configure(target, configure_scope="cloud_init")
    assert plan_ci["planned_stages"] == [StageName.METADATA.value]

    plan_both = LifecyclePlanner.plan_configure(target, configure_scope="both")
    assert plan_both["planned_stages"] == [StageName.BSS.value, StageName.METADATA.value]


# ==============================================================================
# TC_UT_lock_journal_008: Lock and recovery decisions
# ==============================================================================


def test_project_lock_acquire_and_release(tmp_path):
    """Verify free lock acquisition and clean release."""
    lock_file = tmp_path / ".functional_group_mutation.lock"
    lock = ProjectLock(lock_file)

    assert lock.inspect()["status"] == LockStatus.FREE.value

    lock_data = lock.acquire(
        project_name="project_x",
        operation="add",
        target_group="fg_worker_rhel_10_2_x86_64",
        run_id="run-100",
    )
    assert lock_data["project_name"] == "project_x"
    assert lock_data["run_id"] == "run-100"
    assert lock_file.exists()

    # Inspection reports blocked to others because current process is active
    inspection = lock.inspect()
    assert inspection["status"] == LockStatus.BLOCKED.value
    assert inspection["owner_active"] is True

    # Release lock
    assert lock.release(run_id="run-100") is True
    assert not lock_file.exists()
    assert lock.inspect()["status"] == LockStatus.FREE.value


def test_project_lock_contention_blocks_concurrent_mutation(tmp_path):
    """Verify active lock owner blocks concurrent acquisition."""
    lock_file = tmp_path / ".functional_group_mutation.lock"
    lock = ProjectLock(lock_file)

    lock.acquire(
        project_name="project_x",
        operation="add",
        target_group="fg_worker_rhel_10_2_x86_64",
        run_id="run-100",
    )

    with pytest.raises(LockContentionError) as exc_info:
        lock.acquire(
            project_name="project_x",
            operation="remove",
            target_group="fg_other_rhel_10_2_x86_64",
            run_id="run-200",
        )

    assert "Concurrent mutation is blocked" in str(exc_info.value)
    assert "fg_worker_rhel_10_2_x86_64" in str(exc_info.value)


def test_project_lock_refuses_timeout_only_reclamation_for_inactive_owner(tmp_path):
    """FR-5.1: Verify stale lock with dead process is not cleared by timeout alone."""
    lock_file = tmp_path / ".functional_group_mutation.lock"
    # Write lock with a guaranteed non-existent PID
    stale_pid = 99999999
    lock_data = {
        "project_name": "project_x",
        "operation": "add",
        "target_group": "fg_worker_rhel_10_2_x86_64",
        "run_id": "stale-run-001",
        "pid": stale_pid,
        "timestamp": "2026-11-10T10:00:00Z",
        "status": "locked",
    }
    lock_file.write_text(json.dumps(lock_data), encoding="utf-8")

    lock = ProjectLock(lock_file)
    inspection = lock.inspect()
    assert inspection["status"] == LockStatus.RECOVERING.value
    assert inspection["owner_active"] is False

    # Attempting normal acquisition without force_recovery fails closed
    with pytest.raises(RecoveryRequiredError) as exc_info:
        lock.acquire(
            project_name="project_x",
            operation="add",
            target_group="fg_worker_rhel_10_2_x86_64",
            run_id="run-new",
            force_recovery=False,
        )

    assert "Bounded recovery is required before proceeding" in str(exc_info.value)

    # With force_recovery=True, recovery proceeds
    recovered = lock.acquire(
        project_name="project_x",
        operation="add",
        target_group="fg_worker_rhel_10_2_x86_64",
        run_id="run-new",
        force_recovery=True,
    )
    assert recovered["run_id"] == "run-new"


def test_transition_journal_records_stages_and_terminal_outcome(tmp_path):
    """Verify journal persists ordered stage transitions and terminal outcome."""
    journal_file = tmp_path / ".functional_group_journal.json"
    journal = TransitionJournal(journal_file)

    planned = ["smd_group", "bss", "metadata"]
    j = journal.start(
        run_id="run-500",
        project_name="project_x",
        operation="add",
        target_group="fg_ai_rhel_10_2_x86_64",
        planned_stages=planned,
        input_hashes={"config": "abc123hash"},
    )
    assert j.planned_stages == planned
    assert j.completed_stages == []

    # Record stage 1
    journal.record_stage("smd_group", "verified", details={"group_created": True})
    updated = journal.read()
    assert updated.completed_stages == ["smd_group"]
    assert len(updated.stage_records) == 1

    # Record stage 2
    journal.record_stage("bss", "verified", details={"boot_config": "fg_ai"})
    updated = journal.read()
    assert updated.completed_stages == ["smd_group", "bss"]

    # Record stage 3
    journal.record_stage("metadata", "verified")
    updated = journal.read()
    assert updated.completed_stages == ["smd_group", "bss", "metadata"]

    # Finish journal
    finished = journal.finish(terminal_result=TerminalResult.SUCCEEDED.value)
    assert finished.terminal_result == "succeeded"
    assert finished.end_time != ""


def test_bounded_recovery_resumes_from_first_incomplete_stage(tmp_path):
    """FR-5.1: Partial failure recovers by resuming from first incomplete stage."""
    journal_file = tmp_path / ".functional_group_journal.json"
    journal = TransitionJournal(journal_file)

    planned = ["smd_group", "bss", "metadata"]
    journal.start(
        run_id="run-partial",
        project_name="project_x",
        operation="add",
        target_group="fg_ai_rhel_10_2_x86_64",
        planned_stages=planned,
    )
    # smd_group verified, but bss failed
    journal.record_stage("smd_group", "verified")
    journal.record_stage("bss", "failed", details={"error": "BSS connection timeout"})
    journal.finish(
        terminal_result=TerminalResult.RECOVERY_REQUIRED.value,
        error_message="BSS connection timeout",
    )

    j_data = journal.read()
    assert j_data.terminal_result == "recovery_required"
    assert j_data.completed_stages == ["smd_group"]

    # Recovery evaluation determines only incomplete stages remain
    remaining = BoundedRecoveryManager.evaluate_resumption(j_data, planned)
    assert remaining == ["bss", "metadata"]
    assert "smd_group" not in remaining
