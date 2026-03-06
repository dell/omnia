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

"""Unit tests for API schemas."""

# pylint: disable=too-few-public-methods

import pytest
from pydantic import ValidationError

from api.jobs.schemas import (
    CreateJobRequest,
    CreateJobResponse,
    GetJobResponse,
    StageResponse,
    ErrorResponse,
)


class TestCreateJobRequest:
    """Tests for CreateJobRequest schema validation."""

    def test_valid_request_with_required_fields(self):
        """Valid request with required fields should create schema instance."""
        data = {"client_id": "client-123", "client_name": "test-client"}

        request = CreateJobRequest(**data)

        assert request.client_id == "client-123"
        assert request.client_name == "test-client"
        assert request.metadata is None

    def test_valid_request_with_metadata(self):
        """Valid request with metadata should create schema instance."""
        data = {
            "client_id": "client-123",
            "client_name": "test-client",
            "metadata": {"description": "Test", "tags": ["test"]}
        }

        request = CreateJobRequest(**data)

        assert request.client_id == "client-123"
        assert request.client_name == "test-client"
        assert request.metadata == {"description": "Test", "tags": ["test"]}

    def test_missing_client_id_raises_validation_error(self):
        """Missing client_id should raise ValidationError."""
        data = {"client_name": "test-client"}

        with pytest.raises(ValidationError) as exc_info:
            CreateJobRequest(**data)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("client_id",) for e in errors)

    def test_missing_client_name_is_allowed(self):
        """Test method."""
        data = {"client_id": "client-123"}

        request = CreateJobRequest(**data)

        assert request.client_id == "client-123"
        assert request.client_name is None

    def test_empty_client_id_raises_validation_error(self):
        """Test method."""
        data = {"client_id": ""}

        with pytest.raises(ValidationError) as exc_info:
            CreateJobRequest(**data)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("client_id",) for e in errors)

    def test_empty_client_name_raises_validation_error(self):
        """Test method."""
        data = {"client_id": "client-123", "client_name": ""}

        with pytest.raises(ValidationError) as exc_info:
            CreateJobRequest(**data)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("client_name",) for e in errors)

    def test_client_id_max_length_validation(self):
        """Test method."""
        data = {"client_id": "a" * 256}

        with pytest.raises(ValidationError):
            CreateJobRequest(**data)

    def test_client_name_max_length_validation(self):
        """Test method."""
        data = {"client_id": "client-123", "client_name": "a" * 256}

        with pytest.raises(ValidationError):
            CreateJobRequest(**data)

    def test_metadata_can_be_none(self):
        """Test method."""
        data = {"client_id": "client-123", "client_name": "test-client", "metadata": None}

        request = CreateJobRequest(**data)

        assert request.metadata is None


class TestCreateJobResponse:
    """Test class."""

    def test_valid_response_with_all_fields(self):
        """Test method."""
        data = {
            "job_id": "019bf590-1234-7890-abcd-ef1234567890",
            "correlation_id": "019bf590-5678-7890-abcd-ef1234567890",
            "job_state": "CREATED",
            "created_at": "2026-01-25T15:00:00+00:00",
            "stages": []
        }

        response = CreateJobResponse(**data)

        assert response.job_id == "019bf590-1234-7890-abcd-ef1234567890"
        assert response.correlation_id == "019bf590-5678-7890-abcd-ef1234567890"
        assert response.job_state == "CREATED"
        assert response.created_at == "2026-01-25T15:00:00+00:00"
        assert response.stages == []

    def test_missing_required_field_raises_validation_error(self):
        """Test method."""
        data = {
            "job_id": "019bf590-1234-7890-abcd-ef1234567890",
            "job_state": "CREATED",
        }

        with pytest.raises(ValidationError):
            CreateJobResponse(**data)


class TestStageResponse:
    """Test class."""

    def test_valid_stage_response(self):
        """Test method."""
        data = {
            "stage_name": "parse-catalog",
            "stage_state": "PENDING",
            "started_at": None,
            "ended_at": None,
            "error_code": None,
            "error_summary": None,
        }

        stage = StageResponse(**data)

        assert stage.stage_name == "parse-catalog"
        assert stage.stage_state == "PENDING"
        assert stage.started_at is None
        assert stage.ended_at is None

    def test_stage_with_timestamps(self):
        """Test method."""
        data = {
            "stage_name": "parse-catalog",
            "stage_state": "RUNNING",
            "started_at": "2026-01-25T15:00:00Z",
            "ended_at": None,
            "error_code": None,
            "error_summary": None,
        }

        stage = StageResponse(**data)

        assert stage.started_at == "2026-01-25T15:00:00Z"
        assert stage.ended_at is None

    def test_stage_with_error(self):
        """Test method."""
        data = {
            "stage_name": "parse-catalog",
            "stage_state": "FAILED",
            "started_at": "2026-01-25T15:00:00Z",
            "ended_at": "2026-01-25T15:01:00Z",
            "error_code": "CATALOG_PARSE_ERROR",
            "error_summary": "Invalid JSON format",
        }

        stage = StageResponse(**data)

        assert stage.error_code == "CATALOG_PARSE_ERROR"
        assert stage.error_summary == "Invalid JSON format"


class TestGetJobResponse:
    """Test class."""

    def test_valid_get_job_response(self):
        """Test method."""
        data = {
            "job_id": "019bf590-1234-7890-abcd-ef1234567890",
            "correlation_id": "019bf590-5678-7890-abcd-ef1234567890",
            "job_state": "CREATED",
            "created_at": "2026-01-25T15:00:00+00:00",
            "stages": []
        }

        response = GetJobResponse(**data)

        assert response.job_id == "019bf590-1234-7890-abcd-ef1234567890"
        assert response.stages == []


class TestErrorResponse:
    """Test class."""

    def test_valid_error_response(self):
        """Test method."""
        data = {
            "error": "VALIDATION_ERROR",
            "message": "Invalid request",
            "correlation_id": "019bf590-1234-7890-abcd-ef1234567890",
            "timestamp": "2026-01-25T15:00:00Z",
        }

        response = ErrorResponse(**data)

        assert response.error == "VALIDATION_ERROR"
        assert response.message == "Invalid request"
        assert response.correlation_id == "019bf590-1234-7890-abcd-ef1234567890"

    def test_error_response_missing_required_field(self):
        """Test method."""
        data = {
            "error": "VALIDATION_ERROR",
            "message": "Invalid request",
        }

        with pytest.raises(ValidationError):
            ErrorResponse(**data)
