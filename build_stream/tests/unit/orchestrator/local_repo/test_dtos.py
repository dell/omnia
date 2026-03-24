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

"""Unit tests for LocalRepoResponse DTO."""

import uuid
from datetime import datetime, timezone

import pytest

from orchestrator.local_repo.dtos import LocalRepoResponse


class TestLocalRepoResponse:
    """Tests for LocalRepoResponse."""

    @pytest.fixture
    def valid_response_data(self):
        """Provide valid response data."""
        return {
            "job_id": str(uuid.uuid4()),
            "stage_name": "create-local-repository",
            "status": "accepted",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "correlation_id": str(uuid.uuid4()),
        }

    def test_create_response_with_valid_data(self, valid_response_data):
        """Test creating response with valid data."""
        response = LocalRepoResponse(**valid_response_data)

        assert response.job_id == valid_response_data["job_id"]
        assert response.stage_name == valid_response_data["stage_name"]
        assert response.status == valid_response_data["status"]
        assert response.submitted_at == valid_response_data["submitted_at"]
        assert response.correlation_id == valid_response_data["correlation_id"]

    def test_response_is_immutable(self, valid_response_data):
        """Test that response is immutable."""
        response = LocalRepoResponse(**valid_response_data)

        # Attempting to modify should raise AttributeError
        with pytest.raises(AttributeError):
            response.job_id = str(uuid.uuid4())

        with pytest.raises(AttributeError):
            response.stage_name = "other-stage"

        with pytest.raises(AttributeError):
            response.status = "completed"

        with pytest.raises(AttributeError):
            response.submitted_at = datetime.now(timezone.utc).isoformat()

        with pytest.raises(AttributeError):
            response.correlation_id = str(uuid.uuid4())


    def test_response_equality(self, valid_response_data):
        """Test response equality."""
        response1 = LocalRepoResponse(**valid_response_data)
        response2 = LocalRepoResponse(**valid_response_data)

        assert response1 == response2
        assert hash(response1) == hash(response2)

    def test_response_inequality(self, valid_response_data):
        """Test response inequality."""
        response1 = LocalRepoResponse(**valid_response_data)

        # Different job_id
        different_data = valid_response_data.copy()
        different_data["job_id"] = str(uuid.uuid4())
        response2 = LocalRepoResponse(**different_data)

        assert response1 != response2
        assert hash(response1) != hash(response2)

    def test_response_from_domain_entities(self):
        """Test creating response from domain entities."""
        job_id = str(uuid.uuid4())
        stage_name = "create-local-repository"
        status = "accepted"
        submitted_at = datetime.now(timezone.utc).isoformat()
        correlation_id = str(uuid.uuid4())

        response = LocalRepoResponse(
            job_id=job_id,
            stage_name=stage_name,
            status=status,
            submitted_at=submitted_at,
            correlation_id=correlation_id,
        )

        assert isinstance(response.job_id, str)
        assert isinstance(response.stage_name, str)
        assert isinstance(response.status, str)
        assert isinstance(response.submitted_at, str)
        assert isinstance(response.correlation_id, str)

    def test_response_with_different_statuses(self, valid_response_data):
        """Test response with different status values."""
        for status in ["pending", "accepted", "running"]:
            valid_response_data["status"] = status
            response = LocalRepoResponse(**valid_response_data)
            assert response.status == status

    def test_response_repr(self, valid_response_data):
        """Test response string representation."""
        response = LocalRepoResponse(**valid_response_data)

        repr_str = repr(response)
        assert "LocalRepoResponse" in repr_str
        assert valid_response_data["job_id"] in repr_str
        assert valid_response_data["stage_name"] in repr_str
        assert valid_response_data["status"] in repr_str
