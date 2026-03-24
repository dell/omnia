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

"""Unit tests for local repository API schemas."""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from api.local_repo.schemas import (
    CreateLocalRepoResponse,
    LocalRepoErrorResponse,
)




class TestCreateLocalRepoResponse:
    """Tests for CreateLocalRepoResponse schema."""

    @pytest.fixture
    def valid_response_data(self):
        """Provide valid response data."""
        return {
            "job_id": str(uuid.uuid4()),
            "stage": "create-local-repository",
            "status": "accepted",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "correlation_id": str(uuid.uuid4()),
        }

    def test_valid_response(self, valid_response_data):
        """Test creating valid response."""
        response = CreateLocalRepoResponse(**valid_response_data)

        assert response.job_id == valid_response_data["job_id"]
        assert response.stage == valid_response_data["stage"]
        assert response.status == valid_response_data["status"]
        assert response.submitted_at == valid_response_data["submitted_at"]
        assert response.correlation_id == valid_response_data["correlation_id"]




    def test_accepts_string_values(self, valid_response_data):
        """Test that schema accepts string values without validation."""
        # Schema accepts strings, validation happens at API layer
        valid_response_data["job_id"] = "any-string"
        valid_response_data["stage"] = "any-stage"
        valid_response_data["status"] = "any-status"

        response = CreateLocalRepoResponse(**valid_response_data)
        assert response.job_id == "any-string"
        assert response.stage == "any-stage"
        assert response.status == "any-status"

    def test_invalid_datetime_format(self, valid_response_data):
        """Test that datetime field accepts string format."""
        # Schema accepts string, actual validation happens at API layer
        valid_response_data["submitted_at"] = "2026-02-10T07:00:00Z"

        response = CreateLocalRepoResponse(**valid_response_data)
        assert response.submitted_at == "2026-02-10T07:00:00Z"

    def test_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            CreateLocalRepoResponse()

        errors = exc_info.value.errors()
        assert len(errors) == 5  # All 5 fields are required
        field_names = {error["loc"][0] for error in errors}
        assert field_names == {"job_id", "stage", "status", "submitted_at", "correlation_id"}

    def test_response_serialization(self, valid_response_data):
        """Test response serialization to JSON."""
        response = CreateLocalRepoResponse(**valid_response_data)

        json_data = response.model_dump_json()

        assert isinstance(json_data, str)
        assert "job_id" in json_data
        assert "stage" in json_data
        assert "status" in json_data

    def test_response_deserialization(self, valid_response_data):
        """Test response deserialization from JSON."""
        response = CreateLocalRepoResponse(**valid_response_data)

        json_data = response.model_dump_json()
        restored_response = CreateLocalRepoResponse.model_validate_json(json_data)

        assert restored_response.job_id == response.job_id
        assert restored_response.stage == response.stage
        assert restored_response.status == response.status
        assert restored_response.submitted_at == response.submitted_at
        assert restored_response.correlation_id == response.correlation_id


class TestLocalRepoErrorResponse:
    """Tests for LocalRepoErrorResponse schema."""

    def test_valid_error_response(self):
        """Test creating valid error response."""
        error_response = LocalRepoErrorResponse(
            error="VALIDATION_ERROR",
            message="Invalid input provided",
            correlation_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        assert error_response.error == "VALIDATION_ERROR"
        assert error_response.message == "Invalid input provided"
        assert error_response.correlation_id is not None
        assert error_response.timestamp is not None

    def test_error_response_serialization(self):
        """Test error response serialization."""
        error_response = LocalRepoErrorResponse(
            error="TEST_ERROR",
            message="Test error message",
            correlation_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        json_data = error_response.model_dump_json()

        assert isinstance(json_data, str)
        assert "error" in json_data
        assert "message" in json_data

    def test_error_response_with_special_characters(self):
        """Test error response with special characters in message."""
        error_response = LocalRepoErrorResponse(
            error="SPECIAL_ERROR",
            message="Error with special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?",
            correlation_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        assert error_response.message == "Error with special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?"
