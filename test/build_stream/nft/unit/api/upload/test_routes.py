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

"""Unit tests for Upload API routes."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.upload.routes import upload_files
from core.jobs.exceptions import JobNotFoundError, TerminalStateViolationError
from core.jobs.value_objects import ClientId, CorrelationId, JobId
from orchestrator.upload.exceptions import InvalidFilenameError, FileSizeExceededError
from orchestrator.upload.results.upload_files import (
    FileChangeStatus,
    UploadedFileInfo,
    UploadFilesResult,
    UploadSummary,
)


def _uuid():
    return str(uuid.uuid4())


VALID_JOB_ID = "018f3c4b-7b5b-7a9d-b6c4-9f3b4f9b2c10"


def _make_result(job_id=VALID_JOB_ID):
    return UploadFilesResult(
        job_id=job_id,
        upload_summary=UploadSummary(
            total_files=1, changed_files=1, unchanged_files=0,
        ),
        files=[
            UploadedFileInfo(
                filename="network_spec.yml",
                status=FileChangeStatus.CHANGED,
                size_bytes=512,
            )
        ],
    )


class MockUseCase:
    """Mock upload use case."""

    def __init__(self, result=None, error=None):
        self._result = result
        self._error = error

    def execute(self, command):
        if self._error:
            raise self._error
        return self._result or _make_result(str(command.job_id))


def _make_upload_file(filename="network_spec.yml", content=b"key: value"):
    """Create a mock UploadFile."""
    mock = AsyncMock()
    mock.filename = filename
    mock.read = AsyncMock(return_value=content)
    return mock


class TestUploadFilesRoute:
    """Tests for PUT /{job_id}/upload route handler."""

    @pytest.mark.asyncio
    async def test_success(self):
        """Successful upload returns UploadFilesResponse."""
        use_case = MockUseCase()
        token_data = {"client_id": "test-client"}
        corr = CorrelationId(_uuid())
        files = [_make_upload_file()]

        result = await upload_files(
            job_id=VALID_JOB_ID,
            files=files,
            token_data=token_data,
            correlation_id=corr,
            use_case=use_case,
        )

        assert result.job_id == VALID_JOB_ID
        assert result.upload_summary.total_files == 1
        assert result.upload_summary.changed_files == 1
        assert len(result.files) == 1
        assert result.files[0].filename == "network_spec.yml"

    @pytest.mark.asyncio
    async def test_invalid_job_id_returns_400(self):
        """Invalid job_id format raises HTTPException 400."""
        from fastapi import HTTPException

        use_case = MockUseCase()
        token_data = {"client_id": "test-client"}
        corr = CorrelationId(_uuid())
        files = [_make_upload_file()]

        with pytest.raises(HTTPException) as exc_info:
            await upload_files(
                job_id="not-a-uuid",
                files=files,
                token_data=token_data,
                correlation_id=corr,
                use_case=use_case,
            )
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error_code"] == "INVALID_JOB_ID"

    @pytest.mark.asyncio
    async def test_job_not_found_returns_404(self):
        """JobNotFoundError raises HTTPException 404."""
        from fastapi import HTTPException

        use_case = MockUseCase(
            error=JobNotFoundError(VALID_JOB_ID, _uuid())
        )
        token_data = {"client_id": "test-client"}
        corr = CorrelationId(_uuid())
        files = [_make_upload_file()]

        with pytest.raises(HTTPException) as exc_info:
            await upload_files(
                job_id=VALID_JOB_ID,
                files=files,
                token_data=token_data,
                correlation_id=corr,
                use_case=use_case,
            )
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail["error_code"] == "JOB_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_invalid_filename_returns_400(self):
        """InvalidFilenameError raises HTTPException 400."""
        from fastapi import HTTPException

        use_case = MockUseCase(
            error=InvalidFilenameError("bad_file.exe")
        )
        token_data = {"client_id": "test-client"}
        corr = CorrelationId(_uuid())
        files = [_make_upload_file(filename="bad_file.exe")]

        with pytest.raises(HTTPException) as exc_info:
            await upload_files(
                job_id=VALID_JOB_ID,
                files=files,
                token_data=token_data,
                correlation_id=corr,
                use_case=use_case,
            )
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error_code"] == "INVALID_FILENAME"

    @pytest.mark.asyncio
    async def test_file_size_exceeded_returns_400(self):
        """FileSizeExceededError raises HTTPException 400."""
        from fastapi import HTTPException

        use_case = MockUseCase(
            error=FileSizeExceededError("large.yml", 10_000_000)
        )
        token_data = {"client_id": "test-client"}
        corr = CorrelationId(_uuid())
        files = [_make_upload_file()]

        with pytest.raises(HTTPException) as exc_info:
            await upload_files(
                job_id=VALID_JOB_ID,
                files=files,
                token_data=token_data,
                correlation_id=corr,
                use_case=use_case,
            )
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error_code"] == "FILE_SIZE_EXCEEDED"

    @pytest.mark.asyncio
    async def test_terminal_state_returns_409(self):
        """TerminalStateViolationError raises HTTPException 409."""
        from fastapi import HTTPException

        use_case = MockUseCase(
            error=TerminalStateViolationError(
                entity_type="Job",
                entity_id=VALID_JOB_ID,
                state="CLEANED",
                correlation_id=_uuid(),
            )
        )
        token_data = {"client_id": "test-client"}
        corr = CorrelationId(_uuid())
        files = [_make_upload_file()]

        with pytest.raises(HTTPException) as exc_info:
            await upload_files(
                job_id=VALID_JOB_ID,
                files=files,
                token_data=token_data,
                correlation_id=corr,
                use_case=use_case,
            )
        assert exc_info.value.status_code == 409
        assert exc_info.value.detail["error_code"] == "JOB_IN_TERMINAL_STATE"

    @pytest.mark.asyncio
    async def test_unexpected_error_returns_500(self):
        """Unexpected exception raises HTTPException 500."""
        from fastapi import HTTPException

        use_case = MockUseCase(error=RuntimeError("disk full"))
        token_data = {"client_id": "test-client"}
        corr = CorrelationId(_uuid())
        files = [_make_upload_file()]

        with pytest.raises(HTTPException) as exc_info:
            await upload_files(
                job_id=VALID_JOB_ID,
                files=files,
                token_data=token_data,
                correlation_id=corr,
                use_case=use_case,
            )
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail["error_code"] == "INTERNAL_ERROR"
