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

"""Upload API routes."""

from api.logging_utils import log_secure_info
from typing import Annotated, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status


from api.upload.schemas import UploadFilesResponse
from api.upload.dependencies import get_upload_files_use_case
from api.dependencies import verify_token, get_correlation_id
from core.jobs.value_objects import JobId, ClientId, CorrelationId
from core.jobs.exceptions import JobNotFoundError, TerminalStateViolationError
from orchestrator.upload.commands.upload_files import UploadFilesCommand
from orchestrator.upload.exceptions import InvalidFilenameError, FileSizeExceededError
from orchestrator.upload.use_cases.upload_files import UploadFilesUseCase


router = APIRouter(prefix="/jobs", tags=["upload"])


@router.put(
    "/{job_id}/upload",
    response_model=UploadFilesResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload configuration files to a job",
    description="Upload multiple configuration files to a job's artifact directory. "
                "Only whitelisted configuration files are accepted. "
                "Files are stored in multiple locations for audit and playbook consumption.",
)
async def upload_files(
    job_id: str,
    files: List[UploadFile] = File(..., description="Configuration files to upload"),
    token_data: Annotated[dict, Depends(verify_token)] = None,
    correlation_id: CorrelationId = Depends(get_correlation_id),
    use_case: UploadFilesUseCase = Depends(get_upload_files_use_case),
) -> UploadFilesResponse:
    """Upload configuration files to a job.

    Args:
        job_id: Job identifier (UUID v7).
        files: List of files to upload.
        token_data: Token data from authentication (injected).
        correlation_id: Request correlation ID (injected).
        use_case: Upload files use case (injected).

    Returns:
        Upload result with summary and file details.

    Raises:
        HTTPException: On validation or processing errors.
    """
    try:
        # Extract client_id from token
        client_id = ClientId(token_data["client_id"])

        # Parse job ID
        job_id_vo = JobId(job_id)

        # Read file contents
        file_tuples = []
        for upload_file in files:
            content = await upload_file.read()
            file_tuples.append((upload_file.filename, content))

        # Create command
        command = UploadFilesCommand(
            job_id=job_id_vo,
            files=file_tuples,
            client_id=client_id,
            correlation_id=correlation_id,
        )

        # Execute use case
        result = use_case.execute(command)

        # Convert to response schema
        return UploadFilesResponse.from_result(result)

    except InvalidFilenameError as e:
        log_secure_info('warning', f"Invalid filename in upload: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_FILENAME",
                "message": str(e),
            },
        ) from e

    except FileSizeExceededError as e:
        log_secure_info('warning', f"File size exceeded: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "FILE_SIZE_EXCEEDED",
                "message": str(e),
            },
        ) from e

    except ValueError as e:
        # Invalid JobId format
        log_secure_info('warning', f"Invalid job_id format: {job_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_JOB_ID",
                "message": f"Invalid job ID format: {str(e)}",
            },
        ) from e

    except JobNotFoundError as e:
        log_secure_info('warning', f"Job not found: {job_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "JOB_NOT_FOUND",
                "message": str(e),
            },
        ) from e

    except TerminalStateViolationError as e:
        log_secure_info('warning', f"Job in terminal state: {job_id}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "JOB_IN_TERMINAL_STATE",
                "message": str(e),
            },
        ) from e

    except Exception as e:
        log_secure_info('error', f"Unexpected error in upload: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred during upload",
            },
        ) from e
