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

"""Unit tests for Job entity."""

import pytest

from build_stream.core.jobs.entities.job import Job
from build_stream.core.jobs.exceptions import (
    InvalidStateTransitionError,
    TerminalStateViolationError,
)
from build_stream.core.jobs.value_objects import ClientId, JobId, JobState


class TestJob:
    """Tests for Job entity."""

    def test_create_job(self):
        """Job should be created with initial state."""
        job = Job(
            job_id=JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"),
            client_id=ClientId("client-1"),
            request_client_id="req-client-123",
            client_name="abc123",
        )
        assert job.job_state == JobState.CREATED
        assert job.version == 1
        assert job.tombstoned is False

    def test_start_job(self):
        """Job should transition from CREATED to IN_PROGRESS."""
        job = Job(
            job_id=JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"),
            client_id=ClientId("client-1"),
            request_client_id="req-client-123",
            client_name="abc123",
        )
        job.start()
        assert job.job_state == JobState.IN_PROGRESS
        assert job.version == 2

    def test_start_job_invalid_state(self):
        """Starting job from non-CREATED state should fail."""
        job = Job(
            job_id=JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"),
            client_id=ClientId("client-1"),
            request_client_id="req-client-123",
            job_state=JobState.IN_PROGRESS,
            client_name="abc123",
        )
        with pytest.raises(InvalidStateTransitionError):
            job.start()

    def test_complete_job(self):
        """Job should transition from IN_PROGRESS to COMPLETED."""
        job = Job(
            job_id=JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"),
            client_id=ClientId("client-1"),
            request_client_id="req-client-123",
            job_state=JobState.IN_PROGRESS,
            client_name="abc123",
        )
        job.complete()
        assert job.job_state == JobState.COMPLETED
        assert job.version == 2

    def test_complete_job_invalid_state(self):
        """Completing job from non-IN_PROGRESS state should fail."""
        job = Job(
            job_id=JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"),
            client_id=ClientId("client-1"),
            request_client_id="req-client-123",
            client_name="abc123",
        )
        with pytest.raises(InvalidStateTransitionError):
            job.complete()

    def test_fail_job(self):
        """Job should transition from IN_PROGRESS to FAILED."""
        job = Job(
            job_id=JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"),
            client_id=ClientId("client-1"),
            request_client_id="req-client-123",
            job_state=JobState.IN_PROGRESS,
            client_name="abc123",
        )
        job.fail()
        assert job.job_state == JobState.FAILED
        assert job.version == 2

    def test_cancel_job_from_created(self):
        """Job should be cancellable from CREATED state."""
        job = Job(
            job_id=JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"),
            client_id=ClientId("client-1"),
            request_client_id="req-client-123",
            client_name="abc123",
        )
        job.cancel()
        assert job.job_state == JobState.CANCELLED
        assert job.version == 2

    def test_cancel_job_from_in_progress(self):
        """Job should be cancellable from IN_PROGRESS state."""
        job = Job(
            job_id=JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"),
            client_id=ClientId("client-1"),
            request_client_id="req-client-123",
            job_state=JobState.IN_PROGRESS,
            client_name="abc123",
        )
        job.cancel()
        assert job.job_state == JobState.CANCELLED

    def test_terminal_state_prevents_transitions(self):
        """Terminal states should prevent any transitions."""
        job = Job(
            job_id=JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"),
            client_id=ClientId("client-1"),
            request_client_id="req-client-123",
            job_state=JobState.COMPLETED,
            client_name="abc123",
        )
        with pytest.raises(TerminalStateViolationError):
            job.start()
        with pytest.raises(TerminalStateViolationError):
            job.complete()
        with pytest.raises(TerminalStateViolationError):
            job.fail()
        with pytest.raises(TerminalStateViolationError):
            job.cancel()

    def test_tombstone_job(self):
        """Job should be tombstonable."""
        job = Job(
            job_id=JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"),
            client_id=ClientId("client-1"),
            request_client_id="req-client-123",
            job_state=JobState.COMPLETED,
            client_name="abc123",
        )
        job.tombstone()
        assert job.tombstoned is True
        assert job.version == 2

    def test_job_state_predicates(self):
        """Job state predicate methods should work correctly."""
        job = Job(
            job_id=JobId("018f3c4c-6a2e-7b2a-9c2a-3d8d2c4b9a11"),
            client_id=ClientId("client-1"),
            request_client_id="req-client-123",
            job_state=JobState.COMPLETED,
            client_name="abc123",
        )
        assert job.is_completed() is True
        assert job.is_failed() is False
        assert job.is_cancelled() is False
        assert job.is_in_progress() is False
