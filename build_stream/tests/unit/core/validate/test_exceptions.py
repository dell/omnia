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

"""Unit tests for ValidateImageOnTest domain exceptions."""

from core.validate.exceptions import (
    StageGuardViolationError,
    EnvironmentUnavailableError,
    ValidateDomainError,
    ValidationExecutionError,
)


class TestValidateDomainError:
    """Tests for ValidateDomainError base exception."""

    def test_message_stored(self):
        """Error message should be stored."""
        exc = ValidateDomainError("test error", "corr-123")
        assert exc.message == "test error"
        assert exc.correlation_id == "corr-123"

    def test_default_correlation_id(self):
        """Default correlation_id should be empty string."""
        exc = ValidateDomainError("test error")
        assert exc.correlation_id == ""

    def test_str_representation(self):
        """String representation should be the message."""
        exc = ValidateDomainError("test error")
        assert str(exc) == "test error"


class TestEnvironmentUnavailableError:
    """Tests for EnvironmentUnavailableError."""

    def test_inherits_from_base(self):
        """Should inherit from ValidateDomainError."""
        exc = EnvironmentUnavailableError("env down", "corr-456")
        assert isinstance(exc, ValidateDomainError)
        assert exc.message == "env down"
        assert exc.correlation_id == "corr-456"


class TestValidationExecutionError:
    """Tests for ValidationExecutionError."""

    def test_inherits_from_base(self):
        """Should inherit from ValidateDomainError."""
        exc = ValidationExecutionError("exec failed", "corr-789")
        assert isinstance(exc, ValidateDomainError)
        assert exc.message == "exec failed"


class TestStageGuardViolationError:
    """Tests for StageGuardViolationError."""

    def test_inherits_from_base(self):
        """Should inherit from ValidateDomainError."""
        exc = StageGuardViolationError("guard failed", "corr-abc")
        assert isinstance(exc, ValidateDomainError)
        assert exc.message == "guard failed"
