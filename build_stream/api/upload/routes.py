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

import logging
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from dependency_injector.wiring import Provide, inject

from api.upload.schemas import UploadFilesResponse
from container import get_container_class
from core.jobs.value_objects import JobId
from core.jobs.exceptions import JobNotFoundError, TerminalStateViolationError
from orchestrator.upload.commands.upload_files import UploadFilesCommand
from orchestrator.upload.exceptions import InvalidFilenameError, FileSizeExceededError
from orchestrator.upload.use_cases.upload_files import UploadFilesUseCase

logger = logging.getLogger(__name__)

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
@inject
async def upload_files(
    job_id: str,
    files: List[UploadFile] = File(..., description="Configuration files to upload"),
    use_case: UploadFilesUseCase = Depends(Provide[get_container_class().upload_files_use_case]),
) -> UploadFilesResponse:
    """Upload configuration files to a job.
    
    Args:
        job_id: Job identifier (UUID v7).
        files: List of files to upload.
        use_case: Upload files use case (injected).
        
    Returns:
        Upload result with summary and file details.
        
    Raises:
        HTTPException: On validation or processing errors.
    """
    try:
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
        )
        
        # Execute use case
        result = use_case.execute(command)
        
        # Convert to response schema
        return UploadFilesResponse.from_result(result)
        
    except ValueError as e:
        # Invalid JobId format
        logger.warning("Invalid job_id format: %s", job_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_JOB_ID",
                "message": f"Invalid job ID format: {str(e)}",
            },
        )
    
    except JobNotFoundError as e:
        logger.warning("Job not found: %s", job_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "JOB_NOT_FOUND",
                "message": str(e),
            },
        )
    
    except TerminalStateViolationError as e:
        logger.warning("Job in terminal state: %s", job_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "JOB_IN_TERMINAL_STATE",
                "message": str(e),
            },
        )
    
    except InvalidFilenameError as e:
        logger.warning("Invalid filename in upload: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_FILENAME",
                "message": str(e),
            },
        )
    
    except FileSizeExceededError as e:
        logger.warning("File size exceeded: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "FILE_SIZE_EXCEEDED",
                "message": str(e),
            },
        )
    
    except Exception as e:
        logger.error("Unexpected error in upload: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred during upload",
            },
        )
