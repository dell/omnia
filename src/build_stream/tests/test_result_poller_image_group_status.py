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

"""Unit tests for ResultPoller ImageGroup status transitions.

Verifies that:
- Deploy failure does NOT transition ImageGroup to FAILED
- Restart failure does NOT transition ImageGroup to FAILED
- Validate failure DOES transition ImageGroup to FAILED (happy path)
- Restart failure still persists node_results.json and failed_nodes.json
- Resume/retry flows are unaffected
"""

import json
import uuid
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from core.localrepo.entities import PlaybookResult
from core.image_group.entities import ImageGroup
from core.image_group.value_objects import ImageGroupId, ImageGroupStatus
from core.jobs.entities.stage import Stage
from core.jobs.value_objects import JobId, StageName, StageState
from orchestrator.common.result_poller import ResultPoller


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_job_id() -> str:
    """Generate a valid UUID string for use as a job ID."""
    return str(uuid.uuid4())


def _make_image_group(job_id: str, status: ImageGroupStatus) -> ImageGroup:
    """Create a minimal ImageGroup entity."""
    return ImageGroup(
        id=ImageGroupId("test-image-group-v1"),
        job_id=JobId(job_id),
        status=status,
        images=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _make_stage(job_id: str, stage_name: str, state: StageState) -> Stage:
    """Create a Stage entity in the specified state."""
    stage = Stage(
        job_id=JobId(job_id),
        stage_name=StageName(stage_name),
        stage_state=state,
    )
    return stage


def _make_failed_result(job_id: str, stage_name: str, **kwargs) -> PlaybookResult:
    """Create a failed PlaybookResult."""
    defaults = dict(
        job_id=job_id,
        stage_name=stage_name,
        request_id=str(uuid.uuid4()),
        status="failed",
        exit_code=1,
        error_code="PLAYBOOK_FAILED",
        error_summary="Playbook execution failed",
        correlation_id=str(uuid.uuid4()),
    )
    defaults.update(kwargs)
    return PlaybookResult(**defaults)


def _make_success_result(job_id: str, stage_name: str, **kwargs) -> PlaybookResult:
    """Create a successful PlaybookResult."""
    defaults = dict(
        job_id=job_id,
        stage_name=stage_name,
        request_id=str(uuid.uuid4()),
        status="success",
        exit_code=0,
        correlation_id=str(uuid.uuid4()),
    )
    defaults.update(kwargs)
    return PlaybookResult(**defaults)


def _build_poller(
    stage_repo=None,
    job_repo=None,
    audit_repo=None,
    uuid_generator=None,
    image_group_repo=None,
    image_repo=None,
    artifact_store=None,
    artifact_metadata_repo=None,
) -> ResultPoller:
    """Build a ResultPoller with mock dependencies."""
    result_service = MagicMock()

    if uuid_generator is None:
        uuid_generator = MagicMock()
        uuid_generator.generate.return_value = uuid.uuid4()

    if job_repo is None:
        job_repo = MagicMock()
        job_repo.find_by_id.return_value = None

    if stage_repo is None:
        stage_repo = MagicMock()

    if audit_repo is None:
        audit_repo = MagicMock()

    return ResultPoller(
        result_service=result_service,
        job_repo=job_repo,
        stage_repo=stage_repo,
        audit_repo=audit_repo,
        uuid_generator=uuid_generator,
        image_group_repo=image_group_repo,
        image_repo=image_repo,
        artifact_store=artifact_store,
        artifact_metadata_repo=artifact_metadata_repo,
    )


# ===========================================================================
# Test: Deploy failure does NOT mark ImageGroup as FAILED
# ===========================================================================


class TestDeployFailureDoesNotFailImageGroup:
    """Deploy stage failure should NOT transition ImageGroup to FAILED.

    Deploy failures are job-level failures (configuration issues, queue
    problems, etc.) and do not indicate anything wrong with the images.
    """

    def test_deploy_failure_does_not_update_image_group_status(self):
        """When deploy playbook fails, ImageGroup status must NOT change."""
        job_id = _make_job_id()

        # Stage in IN_PROGRESS (as it would be when the playbook is running)
        stage = _make_stage(job_id, "deploy", StageState.IN_PROGRESS)

        # ImageGroup currently in DEPLOYING state
        image_group = _make_image_group(job_id, ImageGroupStatus.DEPLOYING)

        # Mock repositories
        image_group_repo = MagicMock()
        image_group_repo.find_by_job_id.return_value = image_group

        stage_repo = MagicMock()
        stage_repo.find_by_job_and_name.return_value = stage

        poller = _build_poller(
            stage_repo=stage_repo,
            image_group_repo=image_group_repo,
        )

        # Simulate deploy failure result
        result = _make_failed_result(job_id, "deploy")

        # Patch JobStateHelper to avoid side effects
        with patch("orchestrator.common.result_poller.JobStateHelper"):
            poller._on_result_received(result)

        # CRITICAL ASSERTION: update_status must NOT have been called
        # with FAILED status. The ImageGroup should remain in DEPLOYING.
        for c in image_group_repo.update_status.call_args_list:
            _, kwargs = c
            assert kwargs.get("new_status") != ImageGroupStatus.FAILED, (
                "ImageGroup must NOT be set to FAILED on deploy failure"
            )

    def test_deploy_failure_still_fails_the_stage(self):
        """Deploy failure should still mark the Stage as FAILED."""
        job_id = _make_job_id()
        stage = _make_stage(job_id, "deploy", StageState.IN_PROGRESS)

        stage_repo = MagicMock()
        stage_repo.find_by_job_and_name.return_value = stage

        poller = _build_poller(
            stage_repo=stage_repo,
            image_group_repo=MagicMock(),
        )

        result = _make_failed_result(job_id, "deploy")

        with patch("orchestrator.common.result_poller.JobStateHelper"):
            poller._on_result_received(result)

        # Stage must be transitioned to FAILED
        assert stage.stage_state == StageState.FAILED
        assert stage.error_code == "PLAYBOOK_FAILED"

    def test_deploy_failure_still_marks_job_as_failed(self):
        """Deploy failure should still call JobStateHelper.handle_stage_failure."""
        job_id = _make_job_id()
        stage = _make_stage(job_id, "deploy", StageState.IN_PROGRESS)

        stage_repo = MagicMock()
        stage_repo.find_by_job_and_name.return_value = stage

        poller = _build_poller(
            stage_repo=stage_repo,
            image_group_repo=MagicMock(),
        )

        result = _make_failed_result(job_id, "deploy")

        with patch("orchestrator.common.result_poller.JobStateHelper") as mock_helper:
            poller._on_result_received(result)

            # Job should still be marked as FAILED
            mock_helper.handle_stage_failure.assert_called_once()
            call_kwargs = mock_helper.handle_stage_failure.call_args
            assert call_kwargs.kwargs["stage_name"] == "deploy"


# ===========================================================================
# Test: Restart failure does NOT mark ImageGroup as FAILED
# ===========================================================================


class TestRestartFailureDoesNotFailImageGroup:
    """Restart stage failure should NOT transition ImageGroup to FAILED.

    Restart failures are job-level failures and do not indicate anything
    wrong with the images themselves.
    """

    def test_restart_failure_does_not_update_image_group_status(self):
        """When restart playbook fails, ImageGroup status must NOT change."""
        job_id = _make_job_id()
        stage = _make_stage(job_id, "restart", StageState.IN_PROGRESS)

        image_group = _make_image_group(job_id, ImageGroupStatus.RESTARTING)

        image_group_repo = MagicMock()
        image_group_repo.find_by_job_id.return_value = image_group

        stage_repo = MagicMock()
        stage_repo.find_by_job_and_name.return_value = stage

        poller = _build_poller(
            stage_repo=stage_repo,
            image_group_repo=image_group_repo,
        )

        result = _make_failed_result(job_id, "restart")

        with patch("orchestrator.common.result_poller.JobStateHelper"):
            poller._on_result_received(result)

        # CRITICAL ASSERTION: update_status must NOT have been called
        # with FAILED status
        for c in image_group_repo.update_status.call_args_list:
            _, kwargs = c
            assert kwargs.get("new_status") != ImageGroupStatus.FAILED, (
                "ImageGroup must NOT be set to FAILED on restart failure"
            )

    def test_restart_failure_still_fails_the_stage(self):
        """Restart failure should still mark the Stage as FAILED."""
        job_id = _make_job_id()
        stage = _make_stage(job_id, "restart", StageState.IN_PROGRESS)

        stage_repo = MagicMock()
        stage_repo.find_by_job_and_name.return_value = stage

        poller = _build_poller(
            stage_repo=stage_repo,
            image_group_repo=MagicMock(),
        )

        result = _make_failed_result(job_id, "restart")

        with patch("orchestrator.common.result_poller.JobStateHelper"):
            poller._on_result_received(result)

        assert stage.stage_state == StageState.FAILED
        assert stage.error_code == "PLAYBOOK_FAILED"

    def test_restart_failure_still_marks_job_as_failed(self):
        """Restart failure should still call JobStateHelper.handle_stage_failure."""
        job_id = _make_job_id()
        stage = _make_stage(job_id, "restart", StageState.IN_PROGRESS)

        stage_repo = MagicMock()
        stage_repo.find_by_job_and_name.return_value = stage

        poller = _build_poller(
            stage_repo=stage_repo,
            image_group_repo=MagicMock(),
        )

        result = _make_failed_result(job_id, "restart")

        with patch("orchestrator.common.result_poller.JobStateHelper") as mock_helper:
            poller._on_result_received(result)

            mock_helper.handle_stage_failure.assert_called_once()
            call_kwargs = mock_helper.handle_stage_failure.call_args
            assert call_kwargs.kwargs["stage_name"] == "restart"


# ===========================================================================
# Test: Validate failure DOES mark ImageGroup as FAILED (happy path)
# ===========================================================================


class TestValidateFailureMarksImageGroupFailed:
    """Validate stage failure SHOULD transition ImageGroup to FAILED.

    Unlike deploy/restart, validate failure indicates the images did not
    pass validation. This is the only case where ImageGroup -> FAILED.
    """

    def test_validate_failure_sets_image_group_to_failed(self):
        """When validate playbook fails, ImageGroup status MUST become FAILED."""
        job_id = _make_job_id()
        stage = _make_stage(job_id, "validate", StageState.IN_PROGRESS)

        image_group = _make_image_group(job_id, ImageGroupStatus.VALIDATING)

        image_group_repo = MagicMock()
        image_group_repo.find_by_job_id.return_value = image_group

        stage_repo = MagicMock()
        stage_repo.find_by_job_and_name.return_value = stage

        poller = _build_poller(
            stage_repo=stage_repo,
            image_group_repo=image_group_repo,
        )

        result = _make_failed_result(job_id, "validate")

        with patch("orchestrator.common.result_poller.JobStateHelper"):
            poller._on_result_received(result)

        # CRITICAL ASSERTION: update_status MUST be called with FAILED
        image_group_repo.update_status.assert_called_once_with(
            image_group_id=image_group.id,
            new_status=ImageGroupStatus.FAILED,
        )

    def test_validate_failure_also_fails_stage_and_job(self):
        """Validate failure should fail both the stage and job."""
        job_id = _make_job_id()
        stage = _make_stage(job_id, "validate", StageState.IN_PROGRESS)

        image_group = _make_image_group(job_id, ImageGroupStatus.VALIDATING)

        image_group_repo = MagicMock()
        image_group_repo.find_by_job_id.return_value = image_group

        stage_repo = MagicMock()
        stage_repo.find_by_job_and_name.return_value = stage

        poller = _build_poller(
            stage_repo=stage_repo,
            image_group_repo=image_group_repo,
        )

        result = _make_failed_result(job_id, "validate")

        with patch("orchestrator.common.result_poller.JobStateHelper") as mock_helper:
            poller._on_result_received(result)

            # Stage should be FAILED
            assert stage.stage_state == StageState.FAILED

            # Job should also be marked FAILED
            mock_helper.handle_stage_failure.assert_called_once()

    def test_validate_success_sets_image_group_to_passed(self):
        """When validate succeeds, ImageGroup should transition to PASSED."""
        job_id = _make_job_id()
        stage = _make_stage(job_id, "validate", StageState.IN_PROGRESS)

        image_group = _make_image_group(job_id, ImageGroupStatus.VALIDATING)

        image_group_repo = MagicMock()
        image_group_repo.find_by_job_id.return_value = image_group

        stage_repo = MagicMock()
        stage_repo.find_by_job_and_name.return_value = stage

        poller = _build_poller(
            stage_repo=stage_repo,
            image_group_repo=image_group_repo,
        )

        result = _make_success_result(job_id, "validate")

        with patch("orchestrator.common.result_poller.JobStateHelper"):
            poller._on_result_received(result)

        # ImageGroup should transition to PASSED
        image_group_repo.update_status.assert_called_once_with(
            image_group_id=image_group.id,
            new_status=ImageGroupStatus.PASSED,
        )

        # Stage should be COMPLETED
        assert stage.stage_state == StageState.COMPLETED


# ===========================================================================
# Test: Restart failure still persists node_results.json and failed_nodes.json
# ===========================================================================


class TestRestartFailureStillPersistsArtifacts:
    """Restart failure must still persist node_results.json and failed_nodes.json.

    The _on_restart_completed method should be called on both success AND
    failure paths, ensuring artifacts are always captured.
    """

    def test_restart_failure_persists_node_results(self):
        """On restart failure, node_results.json must still be stored as artifact."""
        job_id = _make_job_id()
        stage = _make_stage(job_id, "restart", StageState.IN_PROGRESS)

        stage_repo = MagicMock()
        stage_repo.find_by_job_and_name.return_value = stage

        # Create a temp file simulating node_results.json
        node_results_data = {
            "total_nodes": 5,
            "successful_nodes": 3,
            "failed_nodes": 2,
            "nodes": [
                {"hostname": "node1", "status": "success"},
                {"hostname": "node2", "status": "failed"},
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            node_results_path = Path(tmpdir) / "node_results.json"
            node_results_path.write_text(json.dumps(node_results_data))

            # Also create failed_nodes.json alongside it
            failed_nodes_data = {
                "failure_count": 2,
                "total_nodes": 5,
                "failed_nodes": ["node2", "node4"],
            }
            failed_nodes_path = Path(tmpdir) / "failed_nodes.json"
            failed_nodes_path.write_text(json.dumps(failed_nodes_data))

            # Mock artifact store
            artifact_store = MagicMock()
            artifact_store.store.return_value = "artifact-ref-123"

            artifact_metadata_repo = MagicMock()

            poller = _build_poller(
                stage_repo=stage_repo,
                image_group_repo=MagicMock(),
                artifact_store=artifact_store,
                artifact_metadata_repo=artifact_metadata_repo,
            )

            result = _make_failed_result(
                job_id,
                "restart",
                node_results_file_path=str(node_results_path),
            )

            with patch("orchestrator.common.result_poller.JobStateHelper"):
                poller._on_result_received(result)

            # Artifact store should have been called for both files
            assert artifact_store.store.call_count == 2, (
                "Both node_results.json and failed_nodes.json should be stored"
            )

            # Metadata repo should have been called for both records
            assert artifact_metadata_repo.save.call_count >= 2

    def test_restart_success_also_persists_node_results(self):
        """On restart success, node_results.json must also be stored."""
        job_id = _make_job_id()
        stage = _make_stage(job_id, "restart", StageState.IN_PROGRESS)

        stage_repo = MagicMock()
        stage_repo.find_by_job_and_name.return_value = stage

        node_results_data = {"total_nodes": 5, "successful_nodes": 5}

        with tempfile.TemporaryDirectory() as tmpdir:
            node_results_path = Path(tmpdir) / "node_results.json"
            node_results_path.write_text(json.dumps(node_results_data))

            artifact_store = MagicMock()
            artifact_store.store.return_value = "artifact-ref-456"
            artifact_metadata_repo = MagicMock()

            poller = _build_poller(
                stage_repo=stage_repo,
                image_group_repo=MagicMock(),
                artifact_store=artifact_store,
                artifact_metadata_repo=artifact_metadata_repo,
            )

            result = _make_success_result(
                job_id,
                "restart",
                node_results_file_path=str(node_results_path),
            )

            with patch("orchestrator.common.result_poller.JobStateHelper"):
                poller._on_result_received(result)

            # Artifact store should have been called (at least for node_results)
            assert artifact_store.store.call_count >= 1


# ===========================================================================
# Test: State machine STATUS_FLOW reflects the new behavior
# ===========================================================================


class TestStateMachineStatusFlow:
    """Verify STATUS_FLOW accurately reflects that deploy/restart failures
    do not transition ImageGroup to FAILED."""

    def test_deploy_on_failure_is_none(self):
        """Deploy STATUS_FLOW on_failure should be None."""
        from core.image_group.state_machine import STATUS_FLOW

        _, _, on_failure = STATUS_FLOW["deploy"]
        assert on_failure is None, (
            "Deploy on_failure should be None (no ImageGroup status change)"
        )

    def test_restart_on_failure_is_none(self):
        """Restart STATUS_FLOW on_failure should be None."""
        from core.image_group.state_machine import STATUS_FLOW

        _, _, on_failure = STATUS_FLOW["restart"]
        assert on_failure is None, (
            "Restart on_failure should be None (no ImageGroup status change)"
        )

    def test_validate_on_failure_is_failed(self):
        """Validate STATUS_FLOW on_failure should still be FAILED."""
        from core.image_group.state_machine import STATUS_FLOW

        _, _, on_failure = STATUS_FLOW["validate"]
        assert on_failure == ImageGroupStatus.FAILED, (
            "Validate on_failure should be ImageGroupStatus.FAILED"
        )

    def test_deploy_on_start_is_deploying(self):
        """Deploy STATUS_FLOW on_start should be DEPLOYING."""
        from core.image_group.state_machine import STATUS_FLOW

        on_start, _, _ = STATUS_FLOW["deploy"]
        assert on_start == ImageGroupStatus.DEPLOYING

    def test_restart_on_start_is_restarting(self):
        """Restart STATUS_FLOW on_start should be RESTARTING."""
        from core.image_group.state_machine import STATUS_FLOW

        on_start, _, _ = STATUS_FLOW["restart"]
        assert on_start == ImageGroupStatus.RESTARTING


# ===========================================================================
# Test: Deploy/restart retry still works (ALLOWED_TRANSITIONS)
# ===========================================================================


class TestRetryTransitionsStillWork:
    """Verify that retry/re-run flows are unaffected by the change."""

    def test_deploy_allows_deploying_state_for_retry(self):
        """Deploy should accept DEPLOYING as a starting state (stuck retry)."""
        from core.image_group.state_machine import ALLOWED_TRANSITIONS

        assert ImageGroupStatus.DEPLOYING in ALLOWED_TRANSITIONS["deploy"]

    def test_deploy_allows_failed_state_for_retry(self):
        """Deploy should still accept FAILED state (retry after validate failure)."""
        from core.image_group.state_machine import ALLOWED_TRANSITIONS

        assert ImageGroupStatus.FAILED in ALLOWED_TRANSITIONS["deploy"]

    def test_deploy_allows_restarting_state_for_retry(self):
        """Deploy should accept RESTARTING state (stuck restart retry)."""
        from core.image_group.state_machine import ALLOWED_TRANSITIONS

        assert ImageGroupStatus.RESTARTING in ALLOWED_TRANSITIONS["deploy"]

    def test_deploy_allows_built_state(self):
        """Deploy should accept BUILT state (normal first deploy)."""
        from core.image_group.state_machine import ALLOWED_TRANSITIONS

        assert ImageGroupStatus.BUILT in ALLOWED_TRANSITIONS["deploy"]
