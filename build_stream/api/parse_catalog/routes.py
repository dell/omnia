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

"""FastAPI routes for ParseCatalog API."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from api.dependencies import require_catalog_read, verify_token
from api.parse_catalog.schemas import ErrorResponse, ParseCatalogResponse, ParseCatalogStatus
from api.parse_catalog.service import (
    InvalidFileFormatError,
    InvalidJSONError,
    ParseCatalogService,
)
from core.catalog.exceptions import (
    CatalogParseError,
)
from core.jobs.exceptions import (
    InvalidStateTransitionError,
    JobNotFoundError,
    StageAlreadyCompletedError,
    TerminalStateViolationError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Catalog Parsing"])

_service = ParseCatalogService()


@router.post(
    "/{job_id}/stages/parse-catalog",
    response_model=ParseCatalogResponse,
    status_code=status.HTTP_200_OK,
    summary="Parse a catalog file",
    description="Upload a catalog JSON file to parse and generate output files.",
    responses={
        200: {
            "description": "Catalog parsed successfully",
            "model": ParseCatalogResponse,
        },
        400: {
            "description": "Invalid request (bad file format or JSON)",
            "model": ErrorResponse,
        },
        401: {
            "description": "Unauthorized (missing or invalid token)",
            "model": ErrorResponse,
        },
        403: {
            "description": "Forbidden (insufficient scope)",
            "model": ErrorResponse,
        },
        422: {
            "description": "Validation error",
            "model": ErrorResponse,
        },
        500: {
            "description": "Internal server error during processing",
            "model": ErrorResponse,
        },
    },
)
async def parse_catalog(
    job_id: str,
    file: UploadFile = File(..., description="The catalog JSON file to parse"),
    token_data: Annotated[dict, Depends(verify_token)] = None,  # pylint: disable=unused-argument
    scope_data: Annotated[dict, Depends(require_catalog_read)] = None,  # pylint: disable=unused-argument
) -> ParseCatalogResponse:
    """Parse a catalog from an uploaded JSON file.

    This endpoint accepts a catalog JSON file, validates its format and content,
    then processes it to generate the required output files. Requires a valid
    JWT token and 'catalog:read' scope.

    Args:
        job_id: The job identifier for the parsing operation.
        file: The uploaded JSON file containing catalog data.
        token_data: Validated token data from JWT (injected by dependency).
        scope_data: Token data with validated scope (injected by dependency).

    Returns:
        ParseCatalogResponse with status and message.

    Raises:
        HTTPException: With appropriate status code on failure.
    """
    logger.info(
    "Received parse catalog request for file: %s (job: %s)",
    file.filename,
    job_id,
)

    try:
        contents = await file.read()
        result = await _service.parse_catalog(
            filename=file.filename or "unknown.json",
            contents=contents,
            job_id=job_id,  # Pass job_id to service
        )

        response_data = {
            "status": ParseCatalogStatus.SUCCESS.value,
            "message": result.message,
        }
        return response_data

    except ValueError as e:
        # Handle job_id format validation errors
        error_msg = str(e)
        if "Invalid UUID format" in error_msg or "Invalid job_id format" in error_msg:
            logger.warning("Invalid job_id format: %s", job_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "VALIDATION_ERROR",
                    "message": f"Invalid job_id format: {job_id}",
                    "correlation_id": "test-correlation-id"
                },
            ) from e

        # Re-raise other ValueError as internal error
        logger.exception("Unexpected ValueError processing file: %s", file.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "correlation_id": "test-correlation-id"
            },
        ) from e

    except JobNotFoundError as e:
        logger.warning("Job not found: %s", job_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "JOB_NOT_FOUND",
                "message": f"Job not found: {job_id}",
                "correlation_id": "test-correlation-id"
            },
        ) from e

    except TerminalStateViolationError as e:
        logger.warning("Job in terminal state: %s", job_id)
        # Provide helpful message for terminal state violations
        if e.state == "FAILED":
            message = f"Job {job_id} is in {e.state} state and cannot be retried. Reset the job using /jobs/{job_id}/reset endpoint."
        else:
            message = f"Job {job_id} is in {e.state} state and cannot be modified."
        
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail={
                "error_code": "PRECONDITION_FAILED",
                "message": message,
                "correlation_id": "test-correlation-id"
            },
        ) from e

    except StageAlreadyCompletedError as e:
        logger.warning("Stage already completed: %s", job_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "STAGE_ALREADY_COMPLETED",
                "message": f"Parse catalog stage already completed for job: {job_id}",
                "correlation_id": "test-correlation-id"
            },
        ) from e

    except InvalidStateTransitionError as e:
        logger.warning("Invalid state transition: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "INVALID_STATE_TRANSITION",
                "message": f"Job {job_id}: {str(e)}",
                "correlation_id": "test-correlation-id"
            },
        ) from e

    except InvalidFileFormatError as e:
        logger.warning("Invalid file format: %s", file.filename)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_FILE_FORMAT",
                "message": str(e),
                "correlation_id": "test-correlation-id"
            },
        ) from e

    except InvalidJSONError as e:
        logger.warning("Invalid JSON content in file: %s", file.filename)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_JSON",
                "message": str(e),
                "correlation_id": "test-correlation-id"
            },
        ) from e

    except CatalogParseError as e:
        logger.error("Catalog parsing failed for file: %s", file.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "CATALOG_PARSE_ERROR",
                "message": str(e),
                "correlation_id": "test-correlation-id"
            },
        ) from e

    except Exception as e:
        logger.exception("Unexpected error processing file: %s", file.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "correlation_id": "test-correlation-id"
            },
        ) from e
