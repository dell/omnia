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

"""Unit tests for LocalRepoResultPoller."""

import asyncio
import uuid
from unittest.mock import MagicMock

import pytest

from core.jobs.entities import Stage
from core.jobs.value_objects import (
    JobId,
    StageName,
    StageState,
)
from core.localrepo.entities import PlaybookResult
from orchestrator.local_repo.result_poller import LocalRepoResultPoller


@pytest.fixture
def mock_result_service_fixture():
    """Mock PlaybookQueueResultService."""
    service = MagicMock()
    service.poll_results = MagicMock(return_value=0)
    return service


@pytest.fixture
def mock_stage_repo_fixture():
    """Mock StageRepository."""
    repo = MagicMock()
    return repo


@pytest.fixture
def mock_audit_repo_fixture():
    """Mock AuditEventRepository."""
    repo = MagicMock()
    return repo


@pytest.fixture
def mock_uuid_generator_fixture():
    """Mock UUID generator."""
    generator = MagicMock()
    generator.generate.return_value = str(uuid.uuid4())
    return generator


@pytest.fixture
def result_poller(
    mock_result_service_fixture, mock_stage_repo_fixture, mock_audit_repo_fixture, mock_uuid_generator_fixture
):
    """Create LocalRepoResultPoller instance with mocked dependencies."""
    return LocalRepoResultPoller(
        result_service=mock_result_service_fixture,
        stage_repo=mock_stage_repo_fixture,
        audit_repo=mock_audit_repo_fixture,
        uuid_generator=mock_uuid_generator_fixture,
        poll_interval=1,
    )


class TestLocalRepoResultPoller:
    """Tests for LocalRepoResultPoller."""

    @pytest.mark.asyncio
    async def test_start_starts_polling(self, result_poller, mock_result_service_fixture):
        """Test that start() begins the polling loop."""
        mock_result_service_fixture.poll_results.return_value = 0

        await result_poller.start()
        assert result_poller._running
        await result_poller.stop()

    @pytest.mark.asyncio
    async def test_stop_stops_polling(self, result_poller, mock_result_service_fixture):
        """Test that stop() stops the polling loop."""
        mock_result_service_fixture.poll_results.return_value = 0

        await result_poller.start()
        await result_poller.stop()
        assert not result_poller._running

    @pytest.mark.asyncio
    async def test_poll_loop_calls_poll_results(self, result_poller, mock_result_service_fixture):
        """Test that poll loop calls poll_results with callback."""
        mock_result_service_fixture.poll_results.return_value = 1

        # Start and let it run once
        await result_poller.start()

        # Give it a moment to poll
        await asyncio.sleep(0.1)

        await result_poller.stop()

        # Verify poll_results was called with a callback
        mock_result_service_fixture.poll_results.assert_called()
        callback_arg = mock_result_service_fixture.poll_results.call_args[1]["callback"]
        assert callable(callback_arg)

    def test_on_result_received_success(self, result_poller, mock_stage_repo_fixture, mock_audit_repo_fixture):
        """Test handling successful result."""
        # Setup stage
        job_id = str(uuid.uuid4())
        stage_name = "create-local-repository"
        stage = Stage(
            job_id=JobId(job_id),
            stage_name=StageName(stage_name),
            stage_state=StageState.IN_PROGRESS,
        )
        mock_stage_repo_fixture.find_by_job_and_name.return_value = stage

        # Create result
        result = PlaybookResult(
            job_id=job_id,
            stage_name=stage_name,
            request_id="req-123",
            status="success",
            exit_code=0,
            duration_seconds=30,
        )

        # Handle result
        result_poller._on_result_received(result)

        # Verify stage was completed
        assert stage.stage_state == StageState.COMPLETED
        mock_stage_repo_fixture.save.assert_called_once_with(stage)

        # Verify audit event was created
        mock_audit_repo_fixture.save.assert_called_once()
        audit_event = mock_audit_repo_fixture.save.call_args[0][0]
        assert audit_event.event_type == "STAGE_COMPLETED"
        assert audit_event.job_id == job_id

    def test_on_result_received_failure(self, result_poller, mock_stage_repo_fixture, mock_audit_repo_fixture):
        """Test handling failed result."""
        # Setup stage
        job_id = str(uuid.uuid4())
        stage_name = "create-local-repository"
        stage = Stage(
            job_id=JobId(job_id),
            stage_name=StageName(stage_name),
            stage_state=StageState.IN_PROGRESS,
        )
        mock_stage_repo_fixture.find_by_job_and_name.return_value = stage

        # Create failed result
        result = PlaybookResult(
            job_id=job_id,
            stage_name=stage_name,
            request_id="req-123",
            status="failed",
            exit_code=1,
            error_code="PLAYBOOK_FAILED",
            error_summary="Playbook execution failed",
            duration_seconds=30,
        )

        # Handle result
        result_poller._on_result_received(result)

        # Verify stage was failed
        assert stage.stage_state == StageState.FAILED
        assert stage.error_code == "PLAYBOOK_FAILED"
        assert stage.error_summary == "Playbook execution failed"
        mock_stage_repo_fixture.save.assert_called_once_with(stage)

        # Verify audit event was created
        mock_audit_repo_fixture.save.assert_called_once()
        audit_event = mock_audit_repo_fixture.save.call_args[0][0]
        assert audit_event.event_type == "STAGE_FAILED"

    def test_on_result_received_stage_not_found(self, result_poller, mock_stage_repo_fixture, mock_audit_repo_fixture):
        """Test handling result when stage is not found."""
        # Setup stage not found
        mock_stage_repo_fixture.find_by_job_and_name.return_value = None

        # Create result
        result = PlaybookResult(
            job_id=str(uuid.uuid4()),
            stage_name="create-local-repository",
            request_id="req-123",
            status="success",
            exit_code=0,
        )

        # Handle result
        result_poller._on_result_received(result)

        # Verify nothing was saved
        mock_stage_repo_fixture.save.assert_not_called()
        mock_audit_repo_fixture.save.assert_not_called()

    def test_on_result_received_handles_exceptions(self, result_poller, mock_stage_repo_fixture, mock_audit_repo_fixture):
        """Test that exceptions in result handling are caught."""
        # Setup stage to raise exception
        mock_stage_repo_fixture.find_by_job_and_name.side_effect = Exception("Database error")

        # Create result
        result = PlaybookResult(
            job_id=str(uuid.uuid4()),
            stage_name="create-local-repository",
            request_id="req-123",
            status="success",
            exit_code=0,
        )

        # Should not raise exception
        result_poller._on_result_received(result)

        # Verify nothing was saved due to exception
        mock_stage_repo_fixture.save.assert_not_called()
        mock_audit_repo_fixture.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_poll_loop_handles_exceptions(self, result_poller, mock_result_service_fixture):
        """Test that exceptions in poll loop are caught."""
        # Setup poll_results to raise exception
        mock_result_service_fixture.poll_results.side_effect = Exception("Queue error")

        # Should not raise exception
        await result_poller.start()

        # Give it a moment to poll and encounter error
        await asyncio.sleep(0.1)

        await result_poller.stop()
        assert not result_poller._running
