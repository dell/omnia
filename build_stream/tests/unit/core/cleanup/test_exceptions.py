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

"""Unit tests for Cleanup domain exceptions."""

from core.cleanup.exceptions import (
    AlreadyCleanedError,
    CleanupDomainError,
    CleanupNfsFailedError,
    CleanupS3FailedError,
    CleanupStateInvalidError,
    RetentionLimitExceededError,
)


class TestCleanupDomainError:
    """Tests for CleanupDomainError base exception."""

    def test_is_exception(self):
        """Should be an Exception subclass."""
        exc = CleanupDomainError("cleanup failed")
        assert isinstance(exc, Exception)
        assert str(exc) == "cleanup failed"


class TestCleanupStateInvalidError:
    """Tests for CleanupStateInvalidError."""

    def test_stores_image_group_id_and_status(self):
        """Should store image_group_id and current_status."""
        exc = CleanupStateInvalidError("ig-123", "DEPLOYING")
        assert exc.image_group_id == "ig-123"
        assert exc.current_status == "DEPLOYING"

    def test_message_format(self):
        """Message should include image_group_id and status."""
        exc = CleanupStateInvalidError("ig-123", "VALIDATING")
        assert "ig-123" in exc.message
        assert "VALIDATING" in exc.message
        assert "does not allow cleanup" in exc.message

    def test_inherits_from_base(self):
        """Should inherit from CleanupDomainError."""
        exc = CleanupStateInvalidError("ig-123", "DEPLOYING")
        assert isinstance(exc, CleanupDomainError)

    def test_all_blocked_states(self):
        """Should work for all blocked states: DEPLOYING, RESTARTING, VALIDATING."""
        for state in ("DEPLOYING", "RESTARTING", "VALIDATING"):
            exc = CleanupStateInvalidError("ig-1", state)
            assert exc.current_status == state


class TestAlreadyCleanedError:
    """Tests for AlreadyCleanedError."""

    def test_stores_job_id(self):
        """Should store job_id."""
        exc = AlreadyCleanedError("job-456")
        assert exc.job_id == "job-456"

    def test_message_format(self):
        """Message should include job_id."""
        exc = AlreadyCleanedError("job-456")
        assert "job-456" in exc.message
        assert "already been cleaned" in exc.message

    def test_inherits_from_base(self):
        """Should inherit from CleanupDomainError."""
        exc = AlreadyCleanedError("job-456")
        assert isinstance(exc, CleanupDomainError)


class TestCleanupS3FailedError:
    """Tests for CleanupS3FailedError."""

    def test_stores_fields(self):
        """Should store image_group_id and exit_code."""
        exc = CleanupS3FailedError("ig-789", 1, "access denied")
        assert exc.image_group_id == "ig-789"
        assert exc.exit_code == 1

    def test_message_format(self):
        """Message should include image_group_id and exit_code."""
        exc = CleanupS3FailedError("ig-789", 2, "bucket not found")
        assert "ig-789" in exc.message
        assert "exit code 2" in exc.message

    def test_stderr_truncated(self):
        """Long stderr should be truncated to 500 chars."""
        long_stderr = "x" * 1000
        exc = CleanupS3FailedError("ig-789", 1, long_stderr)
        assert len(exc.message) < 600

    def test_inherits_from_base(self):
        """Should inherit from CleanupDomainError."""
        exc = CleanupS3FailedError("ig-789", 1, "err")
        assert isinstance(exc, CleanupDomainError)


class TestCleanupNfsFailedError:
    """Tests for CleanupNfsFailedError."""

    def test_stores_fields(self):
        """Should store job_id and path."""
        exc = CleanupNfsFailedError("job-111", "/opt/artifacts/job-111", "permission denied")
        assert exc.job_id == "job-111"
        assert exc.path == "/opt/artifacts/job-111"

    def test_message_format(self):
        """Message should include job_id and path."""
        exc = CleanupNfsFailedError("job-111", "/opt/artifacts", "I/O error")
        assert "job-111" in exc.message
        assert "/opt/artifacts" in exc.message

    def test_error_truncated(self):
        """Long error message should be truncated to 500 chars."""
        long_error = "e" * 1000
        exc = CleanupNfsFailedError("job-111", "/path", long_error)
        assert len(exc.message) < 600

    def test_inherits_from_base(self):
        """Should inherit from CleanupDomainError."""
        exc = CleanupNfsFailedError("job-111", "/path", "err")
        assert isinstance(exc, CleanupDomainError)


class TestRetentionLimitExceededError:
    """Tests for RetentionLimitExceededError."""

    def test_stores_count_and_limit(self):
        """Should store current_count and limit."""
        exc = RetentionLimitExceededError(50, 50)
        assert exc.current_count == 50
        assert exc.limit == 50

    def test_message_format(self):
        """Message should include count and limit."""
        exc = RetentionLimitExceededError(50, 50)
        assert "50/50" in exc.message
        assert "retention limit" in exc.message.lower()

    def test_inherits_from_base(self):
        """Should inherit from CleanupDomainError."""
        exc = RetentionLimitExceededError(10, 50)
        assert isinstance(exc, CleanupDomainError)

    def test_over_limit(self):
        """Should work when count exceeds limit."""
        exc = RetentionLimitExceededError(51, 50)
        assert "51/50" in exc.message
