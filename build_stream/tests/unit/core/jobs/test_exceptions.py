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

"""Unit tests for Job domain exceptions."""

import pytest

from build_stream.core.jobs.exceptions import (
    IdempotencyConflictError,
    InvalidStateTransitionError,
    JobAlreadyExistsError,
    JobDomainError,
    JobNotFoundError,
    OptimisticLockError,
    StageNotFoundError,
    TerminalStateViolationError,
)


class TestJobDomainError:
    """Tests for base JobDomainError."""

    def test_basic_error(self):
        """Base error should store message."""
        error = JobDomainError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.correlation_id is None

    def test_error_with_correlation_id(self):
        """Error should store correlation ID."""
        error = JobDomainError("Test error", correlation_id="corr-123")
        assert error.correlation_id == "corr-123"


class TestJobNotFoundError:
    """Tests for JobNotFoundError."""

    def test_error_message(self):
        """Error should include job ID in message."""
        error = JobNotFoundError("job-123")
        assert "job-123" in str(error)
        assert error.job_id == "job-123"

    def test_with_correlation_id(self):
        """Error should store correlation ID."""
        error = JobNotFoundError("job-123", correlation_id="corr-456")
        assert error.correlation_id == "corr-456"


class TestJobAlreadyExistsError:
    """Tests for JobAlreadyExistsError."""

    def test_error_message(self):
        """Error should include job ID in message."""
        error = JobAlreadyExistsError("job-123")
        assert "job-123" in str(error)
        assert error.job_id == "job-123"


class TestInvalidStateTransitionError:
    """Tests for InvalidStateTransitionError."""

    def test_error_message(self):
        """Error should include transition details."""
        error = InvalidStateTransitionError(
            entity_type="Job",
            entity_id="job-123",
            from_state="CREATED",
            to_state="COMPLETED"
        )
        assert "Job" in str(error)
        assert "job-123" in str(error)
        assert "CREATED" in str(error)
        assert "COMPLETED" in str(error)

    def test_error_attributes(self):
        """Error should store all transition details."""
        error = InvalidStateTransitionError(
            entity_type="Stage",
            entity_id="stage-456",
            from_state="PENDING",
            to_state="FAILED"
        )
        assert error.entity_type == "Stage"
        assert error.entity_id == "stage-456"
        assert error.from_state == "PENDING"
        assert error.to_state == "FAILED"


class TestTerminalStateViolationError:
    """Tests for TerminalStateViolationError."""

    def test_error_message(self):
        """Error should include entity and state details."""
        error = TerminalStateViolationError(
            entity_type="Job",
            entity_id="job-123",
            state="COMPLETED"
        )
        assert "Job" in str(error)
        assert "job-123" in str(error)
        assert "COMPLETED" in str(error)
        assert "terminal" in str(error).lower()

    def test_error_attributes(self):
        """Error should store entity details."""
        error = TerminalStateViolationError(
            entity_type="Stage",
            entity_id="stage-456",
            state="FAILED"
        )
        assert error.entity_type == "Stage"
        assert error.entity_id == "stage-456"
        assert error.state == "FAILED"


class TestOptimisticLockError:
    """Tests for OptimisticLockError."""

    def test_error_message(self):
        """Error should include version conflict details."""
        error = OptimisticLockError(
            entity_type="Job",
            entity_id="job-123",
            expected_version=5,
            actual_version=7
        )
        assert "Job" in str(error)
        assert "job-123" in str(error)
        assert "5" in str(error)
        assert "7" in str(error)

    def test_error_attributes(self):
        """Error should store version details."""
        error = OptimisticLockError(
            entity_type="Stage",
            entity_id="stage-456",
            expected_version=2,
            actual_version=3
        )
        assert error.entity_type == "Stage"
        assert error.entity_id == "stage-456"
        assert error.expected_version == 2
        assert error.actual_version == 3


class TestIdempotencyConflictError:
    """Tests for IdempotencyConflictError."""

    def test_error_message(self):
        """Error should include idempotency key and job ID."""
        error = IdempotencyConflictError(
            idempotency_key="key-123",
            existing_job_id="job-456"
        )
        assert "key-123" in str(error)
        assert "job-456" in str(error)
        assert "fingerprint" in str(error).lower()

    def test_error_attributes(self):
        """Error should store idempotency details."""
        error = IdempotencyConflictError(
            idempotency_key="key-789",
            existing_job_id="job-abc"
        )
        assert error.idempotency_key == "key-789"
        assert error.existing_job_id == "job-abc"


class TestStageNotFoundError:
    """Tests for StageNotFoundError."""

    def test_error_message(self):
        """Error should include job ID and stage name."""
        error = StageNotFoundError(
            job_id="job-123",
            stage_name="parse-catalog"
        )
        assert "job-123" in str(error)
        assert "parse-catalog" in str(error)

    def test_error_attributes(self):
        """Error should store job and stage details."""
        error = StageNotFoundError(
            job_id="job-456",
            stage_name="build-image"
        )
        assert error.job_id == "job-456"
        assert error.stage_name == "build-image"
