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

"""Unit tests for Local Repository exceptions."""

import pytest

from core.localrepo.exceptions import (
    InputDirectoryInvalidError,
    InputFilesMissingError,
    LocalRepoDomainError,
    QueueUnavailableError,
)


class TestLocalRepoDomainError:
    """Tests for base domain error."""

    def test_message_stored(self):
        """Error message should be stored."""
        err = LocalRepoDomainError("test error")
        assert err.message == "test error"

    def test_correlation_id_stored(self):
        """Correlation ID should be stored."""
        err = LocalRepoDomainError("test", correlation_id="corr-123")
        assert err.correlation_id == "corr-123"

    def test_correlation_id_defaults_none(self):
        """Correlation ID should default to None."""
        err = LocalRepoDomainError("test")
        assert err.correlation_id is None




class TestQueueUnavailableError:
    """Tests for QueueUnavailableError."""

    def test_attributes_stored(self):
        """Queue path and reason should be stored."""
        err = QueueUnavailableError(queue_path="/queue", reason="not mounted")
        assert err.queue_path == "/queue"
        assert err.reason == "not mounted"


class TestInputFilesMissingError:
    """Tests for InputFilesMissingError."""

    def test_attributes_stored(self):
        """Job ID and input path should be stored."""
        err = InputFilesMissingError(job_id="job-1", input_path="/input")
        assert err.job_id == "job-1"
        assert err.input_path == "/input"

    def test_message_suggests_generate_api(self):
        """Error message should suggest running GenerateInputFiles API."""
        err = InputFilesMissingError(job_id="job-1", input_path="/input")
        assert "GenerateInputFiles" in err.message


class TestInputDirectoryInvalidError:
    """Tests for InputDirectoryInvalidError."""

    def test_attributes_stored(self):
        """All attributes should be stored."""
        err = InputDirectoryInvalidError(
            job_id="job-1", input_path="/input", reason="empty"
        )
        assert err.job_id == "job-1"
        assert err.input_path == "/input"
        assert err.reason == "empty"
