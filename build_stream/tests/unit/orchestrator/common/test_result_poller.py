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

"""Unit tests for common ResultPoller."""

import asyncio
import uuid

import pytest

from core.jobs.entities import Stage
from core.jobs.value_objects import (
    JobId,
    StageName,
    StageState,
)
from core.localrepo.entities import PlaybookResult
from orchestrator.common.result_poller import ResultPoller


# --- Mock dependencies ---

class MockResultService:
    def __init__(self):
        self.callback = None
        self.results_to_deliver = []

    def poll_results(self, callback):
        self.callback = callback
        count = 0
        for result in self.results_to_deliver:
            callback(result)
            count += 1
        self.results_to_deliver = []
        return count


class MockStageRepo:
    def __init__(self):
        self._stages = {}

    def save(self, stage):
        key = (str(stage.job_id), stage.stage_name.value)
        self._stages[key] = stage

    def find_by_job_and_name(self, job_id, stage_name):
        return self._stages.get((str(job_id), stage_name.value))


class MockAuditRepo:
    def __init__(self):
        self._events = []

    def save(self, event):
        self._events.append(event)

    def find_by_job(self, job_id):
        return [e for e in self._events if str(e.job_id) == str(job_id)]


class MockUUIDGenerator:
    def generate(self):
        return uuid.uuid4()


# --- Fixtures ---

@pytest.fixture
def mock_result_service():
    return MockResultService()


@pytest.fixture
def mock_stage_repo():
    return MockStageRepo()


@pytest.fixture
def mock_audit_repo():
    return MockAuditRepo()


@pytest.fixture
def mock_uuid_gen():
    return MockUUIDGenerator()


@pytest.fixture
def result_poller(mock_result_service, mock_stage_repo, mock_audit_repo, mock_uuid_gen):
    """Create ResultPoller instance with mocked dependencies."""
    return ResultPoller(
        result_service=mock_result_service,
        stage_repo=mock_stage_repo,
        audit_repo=mock_audit_repo,
        uuid_generator=mock_uuid_gen,
        poll_interval=1,
    )


# --- Tests ---

class TestResultPoller:
    """Tests for common ResultPoller."""

    @pytest.mark.asyncio
    async def test_start_starts_polling(self, result_poller, mock_result_service):
        """Poller should start and begin polling."""
        await result_poller.start()
        assert result_poller._running is True
        assert result_poller._task is not None
        await result_poller.stop()

    @pytest.mark.asyncio
    async def test_stop_stops_polling(self, result_poller):
        """Poller should stop cleanly."""
        await result_poller.start()
        await result_poller.stop()
        assert result_poller._running is False

    @pytest.mark.asyncio
    async def test_double_start_is_safe(self, result_poller):
        """Starting twice should not create duplicate tasks."""
        await result_poller.start()
        await result_poller.start()  # Should log warning, not error
        assert result_poller._running is True
        await result_poller.stop()

    @pytest.mark.asyncio
    async def test_stop_without_start_is_safe(self, result_poller):
        """Stopping without starting should be a no-op."""
        await result_poller.stop()
        assert result_poller._running is False

    def test_on_result_success(
        self, result_poller, mock_stage_repo, mock_audit_repo
    ):
        """Successful result should complete the stage and emit audit event."""
        job_id = JobId(str(uuid.uuid4()))
        stage = Stage(
            job_id=job_id,
            stage_name=StageName("validate-image-on-test"),
            stage_state=StageState.IN_PROGRESS,
            attempt=1,
        )
        mock_stage_repo.save(stage)

        result = PlaybookResult(
            job_id=str(job_id),
            stage_name="validate-image-on-test",
            request_id=str(uuid.uuid4()),
            status="success",
            exit_code=0,
            duration_seconds=120,
        )

        result_poller._on_result_received(result)

        saved = mock_stage_repo.find_by_job_and_name(
            str(job_id), StageName("validate-image-on-test")
        )
        assert saved.stage_state == StageState.COMPLETED
        assert len(mock_audit_repo._events) == 1
        assert mock_audit_repo._events[0].event_type == "STAGE_COMPLETED"

    def test_on_result_failure(
        self, result_poller, mock_stage_repo, mock_audit_repo
    ):
        """Failed result should fail the stage and emit audit event."""
        job_id = JobId(str(uuid.uuid4()))
        stage = Stage(
            job_id=job_id,
            stage_name=StageName("validate-image-on-test"),
            stage_state=StageState.IN_PROGRESS,
            attempt=1,
        )
        mock_stage_repo.save(stage)

        result = PlaybookResult(
            job_id=str(job_id),
            stage_name="validate-image-on-test",
            request_id=str(uuid.uuid4()),
            status="failed",
            exit_code=1,
            error_code="PLAYBOOK_EXECUTION_FAILED",
            error_summary="Playbook exited with code 1",
        )

        result_poller._on_result_received(result)

        saved = mock_stage_repo.find_by_job_and_name(
            str(job_id), StageName("validate-image-on-test")
        )
        assert saved.stage_state == StageState.FAILED
        assert len(mock_audit_repo._events) == 1
        assert mock_audit_repo._events[0].event_type == "STAGE_FAILED"

    def test_on_result_stage_not_found(
        self, result_poller, mock_stage_repo, mock_audit_repo
    ):
        """Missing stage should be handled gracefully (no crash)."""
        result = PlaybookResult(
            job_id=str(uuid.uuid4()),
            stage_name="validate-image-on-test",
            request_id=str(uuid.uuid4()),
            status="success",
            exit_code=0,
        )

        # Should not raise
        result_poller._on_result_received(result)
        assert len(mock_audit_repo._events) == 0

    def test_backward_compatibility_alias(self):
        """LocalRepoResultPoller should be an alias for ResultPoller."""
        from orchestrator.local_repo.result_poller import LocalRepoResultPoller
        assert LocalRepoResultPoller is ResultPoller
