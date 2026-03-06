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

"""Unit tests for SQL repository implementations (without database)."""

import pytest
from unittest.mock import Mock, MagicMock

from core.jobs.entities.job import Job
from core.jobs.exceptions import OptimisticLockError
from core.jobs.value_objects import ClientId, JobId, JobState
from infra.db.models import JobModel
from infra.db.repositories import SqlJobRepository


class TestSqlJobRepositoryUnit:
    """Unit tests for SqlJobRepository using mocks."""

    def test_save_raises_optimistic_lock_error_on_conflict(self) -> None:
        """Test that save raises OptimisticLockError when version conflicts."""
        # Mock session that simulates a version conflict
        mock_session = Mock()
        mock_existing = Mock()
        mock_existing.version = 5  # Different from expected
        
        # Configure get to return existing record
        mock_session.get.return_value = mock_existing
        
        repo = SqlJobRepository(mock_session)
        
        job = Job(
            job_id=JobId("12345678-1234-5678-9abc-123456789abc"),
            client_id=ClientId("test-client"),
            request_client_id="req-123",
            job_state=JobState.IN_PROGRESS,
            version=3,  # Stale version (expected version would be 4)
        )
        
        with pytest.raises(OptimisticLockError) as exc_info:
            repo.save(job)
        
        assert "Version conflict for Job" in str(exc_info.value)
        assert exc_info.value.expected_version == 2  # version - 1
        assert exc_info.value.actual_version == 5

    def test_save_calls_flush(self) -> None:
        """Test that save calls session.flush()."""
        mock_session = Mock()
        mock_session.get.return_value = None  # No existing record
        
        repo = SqlJobRepository(mock_session)
        
        job = Job(
            job_id=JobId("12345678-1234-5678-9abc-123456789abc"),
            client_id=ClientId("test-client"),
            request_client_id="req-123",
        )
        
        repo.save(job)
        
        # Verify flush was called
        mock_session.flush.assert_called_once()

    def test_find_by_id_returns_none_when_not_found(self) -> None:
        """Test that find_by_id returns None when job doesn't exist."""
        mock_session = Mock()
        mock_session.get.return_value = None
        
        repo = SqlJobRepository(mock_session)
        
        result = repo.find_by_id(JobId("12345678-1234-5678-9abc-123456789abc"))
        
        assert result is None
        mock_session.get.assert_called_once_with(JobModel, "12345678-1234-5678-9abc-123456789abc")

    def test_exists_returns_true_when_found(self) -> None:
        """Test that exists returns True when job exists."""
        mock_session = Mock()
        mock_result = Mock()
        mock_result.first.return_value = mock_result
        mock_session.execute.return_value = mock_result
        
        repo = SqlJobRepository(mock_session)
        
        result = repo.exists(JobId("12345678-1234-5678-9abc-123456789abc"))
        
        assert result is True

    def test_exists_returns_false_when_not_found(self) -> None:
        """Test that exists returns False when job doesn't exist."""
        mock_session = Mock()
        mock_result = Mock()
        mock_result.first.return_value = None
        mock_session.execute.return_value = mock_result
        
        repo = SqlJobRepository(mock_session)
        
        result = repo.exists(JobId("87654321-4321-8765-cba9-876543210cba"))
        
        assert result is False
