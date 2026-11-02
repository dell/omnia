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

"""Unit tests for Parse Catalog API routes."""

import json
import uuid
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, UploadFile, status

from api.parse_catalog.routes import parse_catalog
from api.parse_catalog.service import (
    InvalidFileFormatError,
    InvalidJSONError,
    ParseResult,
)
from core.catalog.exceptions import CatalogParseError
from core.jobs.exceptions import (
    InvalidStateTransitionError,
    JobNotFoundError,
    StageAlreadyCompletedError,
    TerminalStateViolationError,
)


def create_test_uuid():
    """Helper to create valid UUIDs for testing."""
    return str(uuid.uuid4())


class MockParseCatalogUseCase:
    """Mock use case for testing."""

    def __init__(self, error_to_raise=None):
        """Initialize mock with optional failure."""
        self.error_to_raise = error_to_raise
        self.executed_commands = []

    def execute(self, command):
        """Mock execute method."""
        self.executed_commands.append(command)
        if self.error_to_raise:
            raise self.error_to_raise

        return MagicMock(
            success=True,
            message="Catalog parsed successfully"
        )


class MockDBSession:
    """Mock database session."""

    def __init__(self):
        self.committed = False
        self.rolled_back = False
        self.is_active = True

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def create_mock_upload_file(filename: str, content: bytes):
    """Create a mock UploadFile for testing."""
    file_obj = BytesIO(content)
    upload_file = UploadFile(
        file=file_obj,
        filename=filename,
    )
    # Make read async-compatible
    upload_file.read = AsyncMock(return_value=content)
    return upload_file


@pytest.mark.asyncio
class TestParseCatalogRoutes:
    """Test cases for parse catalog routes."""

    async def test_parse_catalog_success(self):
        """Test successful catalog parsing."""
        test_job_id = create_test_uuid()
        use_case = MockParseCatalogUseCase()
        db_session = MockDBSession()

        catalog_data = {"roles": ["role1", "role2"]}
        file_content = json.dumps(catalog_data).encode('utf-8')
        upload_file = create_mock_upload_file("catalog.json", file_content)

        response = await parse_catalog(
            job_id=test_job_id,
            file=upload_file,
            token_data={"client_id": "client-123"},
            scope_data={"scope": "catalog:read"},
            parse_catalog_use_case=use_case,
            db_session=db_session,
        )

        assert response["status"] == "success"
        assert response["message"] == "Catalog parsed successfully"
        assert len(use_case.executed_commands) == 1

    async def test_parse_catalog_invalid_file_format(self):
        """Test with invalid file format (not .json)."""
        test_job_id = create_test_uuid()
        use_case = MockParseCatalogUseCase(
            error_to_raise=InvalidFileFormatError("Invalid file format. Only JSON files are accepted.")
        )
        db_session = MockDBSession()

        file_content = b"some content"
        upload_file = create_mock_upload_file("catalog.txt", file_content)

        with pytest.raises(HTTPException) as exc_info:
            await parse_catalog(
                job_id=test_job_id,
                file=upload_file,
                token_data={"client_id": "client-123"},
                scope_data={"scope": "catalog:read"},
                parse_catalog_use_case=use_case,
                db_session=db_session,
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        detail = exc_info.value.detail
        assert detail["error_code"] == "INVALID_FILE_FORMAT"
        assert "JSON files" in detail["message"]

    async def test_parse_catalog_invalid_json(self):
        """Test with invalid JSON content."""
        test_job_id = create_test_uuid()
        use_case = MockParseCatalogUseCase(
            error_to_raise=InvalidJSONError("Invalid JSON data: Expecting ',' delimiter")
        )
        db_session = MockDBSession()

        file_content = b'{"invalid": json}'
        upload_file = create_mock_upload_file("catalog.json", file_content)

        with pytest.raises(HTTPException) as exc_info:
            await parse_catalog(
                job_id=test_job_id,
                file=upload_file,
                token_data={"client_id": "client-123"},
                scope_data={"scope": "catalog:read"},
                parse_catalog_use_case=use_case,
                db_session=db_session,
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        detail = exc_info.value.detail
        assert detail["error_code"] == "INVALID_JSON"
        assert "Invalid JSON data" in detail["message"]

    async def test_parse_catalog_job_not_found(self):
        """Test when job is not found."""
        test_job_id = create_test_uuid()
        use_case = MockParseCatalogUseCase(
            error_to_raise=JobNotFoundError("Job not found", test_job_id)
        )
        db_session = MockDBSession()

        catalog_data = {"roles": ["role1"]}
        file_content = json.dumps(catalog_data).encode('utf-8')
        upload_file = create_mock_upload_file("catalog.json", file_content)

        with pytest.raises(HTTPException) as exc_info:
            await parse_catalog(
                job_id=test_job_id,
                file=upload_file,
                token_data={"client_id": "client-123"},
                scope_data={"scope": "catalog:read"},
                parse_catalog_use_case=use_case,
                db_session=db_session,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        detail = exc_info.value.detail
        assert detail["error_code"] == "JOB_NOT_FOUND"
        assert test_job_id in detail["message"]

    async def test_parse_catalog_terminal_state_violation(self):
        """Test when job is in terminal state."""
        test_job_id = create_test_uuid()
        use_case = MockParseCatalogUseCase(
            error_to_raise=TerminalStateViolationError("Job", test_job_id, "COMPLETED")
        )
        db_session = MockDBSession()

        catalog_data = {"roles": ["role1"]}
        file_content = json.dumps(catalog_data).encode('utf-8')
        upload_file = create_mock_upload_file("catalog.json", file_content)

        with pytest.raises(HTTPException) as exc_info:
            await parse_catalog(
                job_id=test_job_id,
                file=upload_file,
                token_data={"client_id": "client-123"},
                scope_data={"scope": "catalog:read"},
                parse_catalog_use_case=use_case,
                db_session=db_session,
            )

        assert exc_info.value.status_code == status.HTTP_412_PRECONDITION_FAILED
        detail = exc_info.value.detail
        assert detail["error_code"] == "PRECONDITION_FAILED"
        assert "terminal state" in detail["message"]

    async def test_parse_catalog_stage_already_completed(self):
        """Test when stage is already completed."""
        test_job_id = create_test_uuid()
        use_case = MockParseCatalogUseCase(
            error_to_raise=StageAlreadyCompletedError("Stage", test_job_id, "parse-catalog")
        )
        db_session = MockDBSession()

        catalog_data = {"roles": ["role1"]}
        file_content = json.dumps(catalog_data).encode('utf-8')
        upload_file = create_mock_upload_file("catalog.json", file_content)

        with pytest.raises(HTTPException) as exc_info:
            await parse_catalog(
                job_id=test_job_id,
                file=upload_file,
                token_data={"client_id": "client-123"},
                scope_data={"scope": "catalog:read"},
                parse_catalog_use_case=use_case,
                db_session=db_session,
            )

        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
        detail = exc_info.value.detail
        assert detail["error_code"] == "STAGE_ALREADY_COMPLETED"
        assert "already completed" in detail["message"]

    async def test_parse_catalog_invalid_state_transition(self):
        """Test when state transition is invalid."""
        test_job_id = create_test_uuid()
        use_case = MockParseCatalogUseCase(
            error_to_raise=InvalidStateTransitionError("Stage", test_job_id, "COMPLETED", "PENDING", create_test_uuid())
        )
        db_session = MockDBSession()

        catalog_data = {"roles": ["role1"]}
        file_content = json.dumps(catalog_data).encode('utf-8')
        upload_file = create_mock_upload_file("catalog.json", file_content)

        with pytest.raises(HTTPException) as exc_info:
            await parse_catalog(
                job_id=test_job_id,
                file=upload_file,
                token_data={"client_id": "client-123"},
                scope_data={"scope": "catalog:read"},
                parse_catalog_use_case=use_case,
                db_session=db_session,
            )

        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
        detail = exc_info.value.detail
        assert detail["error_code"] == "INVALID_STATE_TRANSITION"

    async def test_parse_catalog_parse_error(self):
        """Test when catalog parsing fails."""
        test_job_id = create_test_uuid()
        use_case = MockParseCatalogUseCase(
            error_to_raise=CatalogParseError("Failed to parse catalog")
        )
        db_session = MockDBSession()

        catalog_data = {"roles": ["role1"]}
        file_content = json.dumps(catalog_data).encode('utf-8')
        upload_file = create_mock_upload_file("catalog.json", file_content)

        with pytest.raises(HTTPException) as exc_info:
            await parse_catalog(
                job_id=test_job_id,
                file=upload_file,
                token_data={"client_id": "client-123"},
                scope_data={"scope": "catalog:read"},
                parse_catalog_use_case=use_case,
                db_session=db_session,
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        detail = exc_info.value.detail
        assert detail["error_code"] == "CATALOG_PARSE_ERROR"

    async def test_parse_catalog_invalid_job_id_format(self):
        """Test with invalid job ID format."""
        use_case = MockParseCatalogUseCase(
            error_to_raise=ValueError("Invalid UUID format: not-a-uuid")
        )
        db_session = MockDBSession()

        catalog_data = {"roles": ["role1"]}
        file_content = json.dumps(catalog_data).encode('utf-8')
        upload_file = create_mock_upload_file("catalog.json", file_content)

        with pytest.raises(HTTPException) as exc_info:
            await parse_catalog(
                job_id="not-a-uuid",
                file=upload_file,
                token_data={"client_id": "client-123"},
                scope_data={"scope": "catalog:read"},
                parse_catalog_use_case=use_case,
                db_session=db_session,
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        detail = exc_info.value.detail
        assert detail["error_code"] == "VALIDATION_ERROR"
        assert "Invalid job_id format" in detail["message"]

    async def test_parse_catalog_unexpected_error(self):
        """Test with unexpected error."""
        test_job_id = create_test_uuid()
        use_case = MockParseCatalogUseCase(
            error_to_raise=RuntimeError("Unexpected error")
        )
        db_session = MockDBSession()

        catalog_data = {"roles": ["role1"]}
        file_content = json.dumps(catalog_data).encode('utf-8')
        upload_file = create_mock_upload_file("catalog.json", file_content)

        with pytest.raises(HTTPException) as exc_info:
            await parse_catalog(
                job_id=test_job_id,
                file=upload_file,
                token_data={"client_id": "client-123"},
                scope_data={"scope": "catalog:read"},
                parse_catalog_use_case=use_case,
                db_session=db_session,
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        detail = exc_info.value.detail
        assert detail["error_code"] == "INTERNAL_ERROR"
        assert "unexpected error" in detail["message"].lower()

    async def test_parse_catalog_with_no_filename(self):
        """Test parsing with no filename provided."""
        test_job_id = create_test_uuid()
        use_case = MockParseCatalogUseCase()
        db_session = MockDBSession()

        catalog_data = {"roles": ["role1", "role2"]}
        file_content = json.dumps(catalog_data).encode('utf-8')
        upload_file = create_mock_upload_file(None, file_content)

        response = await parse_catalog(
            job_id=test_job_id,
            file=upload_file,
            token_data={"client_id": "client-123"},
            scope_data={"scope": "catalog:read"},
            parse_catalog_use_case=use_case,
            db_session=db_session,
        )

        assert response["status"] == "success"
        # Verify use case was still called
        assert len(use_case.executed_commands) == 1
