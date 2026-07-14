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

"""Unit tests for Deploy domain exceptions."""

from core.deploy.exceptions import (
    DeployDomainError,
    DeployExecutionError,
    EnvironmentUnavailableError,
    StageGuardViolationError,
)


class TestDeployDomainError:
    """Tests for DeployDomainError base exception."""

    def test_message_stored(self):
        """Error message and correlation_id should be stored."""
        exc = DeployDomainError("deploy failed", "corr-123")
        assert exc.message == "deploy failed"
        assert exc.correlation_id == "corr-123"

    def test_default_correlation_id(self):
        """Default correlation_id should be empty string."""
        exc = DeployDomainError("deploy failed")
        assert exc.correlation_id == ""

    def test_str_representation(self):
        """String representation should be the message."""
        exc = DeployDomainError("deploy failed")
        assert str(exc) == "deploy failed"

    def test_is_exception(self):
        """Should be an Exception subclass."""
        exc = DeployDomainError("test")
        assert isinstance(exc, Exception)


class TestEnvironmentUnavailableError:
    """Tests for EnvironmentUnavailableError."""

    def test_inherits_from_base(self):
        """Should inherit from DeployDomainError."""
        exc = EnvironmentUnavailableError("env down", "corr-456")
        assert isinstance(exc, DeployDomainError)
        assert exc.message == "env down"
        assert exc.correlation_id == "corr-456"


class TestDeployExecutionError:
    """Tests for DeployExecutionError."""

    def test_inherits_from_base(self):
        """Should inherit from DeployDomainError."""
        exc = DeployExecutionError("exec failed", "corr-789")
        assert isinstance(exc, DeployDomainError)
        assert exc.message == "exec failed"

    def test_catchable_as_base(self):
        """Should be catchable as DeployDomainError."""
        try:
            raise DeployExecutionError("exec failed", "corr-789")
        except DeployDomainError as caught:
            assert caught.message == "exec failed"


class TestStageGuardViolationError:
    """Tests for StageGuardViolationError."""

    def test_inherits_from_base(self):
        """Should inherit from DeployDomainError."""
        exc = StageGuardViolationError("guard failed", "corr-abc")
        assert isinstance(exc, DeployDomainError)
        assert exc.message == "guard failed"

    def test_catchable_as_base(self):
        """Should be catchable as DeployDomainError."""
        try:
            raise StageGuardViolationError("guard failed")
        except DeployDomainError as caught:
            assert caught.message == "guard failed"
