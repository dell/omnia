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

"""Unit tests for CreateLocalRepoCommand."""

import uuid

import pytest

from core.jobs.value_objects import ClientId, CorrelationId, JobId
from orchestrator.local_repo.commands import CreateLocalRepoCommand


class TestCreateLocalRepoCommand:
    """Tests for CreateLocalRepoCommand."""

    @pytest.fixture
    def valid_command_data(self):
        """Provide valid command data."""
        return {
            "job_id": JobId(str(uuid.uuid4())),
            "client_id": ClientId("test-client-123"),
            "correlation_id": CorrelationId(str(uuid.uuid4())),
        }

    def test_create_command_with_valid_data(self, valid_command_data):
        """Test creating command with valid data."""
        command = CreateLocalRepoCommand(**valid_command_data)

        assert command.job_id == valid_command_data["job_id"]
        assert command.client_id == valid_command_data["client_id"]
        assert command.correlation_id == valid_command_data["correlation_id"]

    def test_command_is_immutable(self, valid_command_data):
        """Test that command is immutable."""
        command = CreateLocalRepoCommand(**valid_command_data)

        # Attempting to modify should raise AttributeError
        with pytest.raises(AttributeError):
            command.job_id = JobId(str(uuid.uuid4()))

        with pytest.raises(AttributeError):
            command.client_id = ClientId("other-client")

        with pytest.raises(AttributeError):
            command.correlation_id = CorrelationId(str(uuid.uuid4()))

    def test_command_equality(self, valid_command_data):
        """Test command equality."""
        command1 = CreateLocalRepoCommand(**valid_command_data)
        command2 = CreateLocalRepoCommand(**valid_command_data)

        assert command1 == command2
        assert hash(command1) == hash(command2)

    def test_command_inequality(self, valid_command_data):
        """Test command inequality."""
        command1 = CreateLocalRepoCommand(**valid_command_data)

        # Different job_id
        different_data = valid_command_data.copy()
        different_data["job_id"] = JobId(str(uuid.uuid4()))
        command2 = CreateLocalRepoCommand(**different_data)

        assert command1 != command2
        assert hash(command1) != hash(command2)

    def test_command_repr(self, valid_command_data):
        """Test command string representation."""
        command = CreateLocalRepoCommand(**valid_command_data)

        repr_str = repr(command)
        assert "CreateLocalRepoCommand" in repr_str
        assert str(valid_command_data["job_id"]) in repr_str
        assert str(valid_command_data["client_id"]) in repr_str
        assert str(valid_command_data["correlation_id"]) in repr_str

    def test_command_with_none_correlation_id(self):
        """Test creating command with None correlation_id."""
        command = CreateLocalRepoCommand(
            job_id=JobId(str(uuid.uuid4())),
            client_id=ClientId("test-client"),
            correlation_id=None,
        )

        assert command.correlation_id is None

    def test_command_accepts_valid_value_objects(self, valid_command_data):
        """Test that command accepts properly validated value objects."""
        command = CreateLocalRepoCommand(**valid_command_data)

        assert command.job_id == valid_command_data["job_id"]
        assert command.client_id == valid_command_data["client_id"]
        assert command.correlation_id == valid_command_data["correlation_id"]
