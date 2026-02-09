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

from api.dependencies import require_catalog_read
from .schemas import ErrorResponse, ParseCatalogResponse, ParseCatalogStatus
from .service import (
    CatalogParseError,
    InvalidFileFormatError,
    InvalidJSONError,
    ParseCatalogService,
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
    token_data: Annotated[dict, Depends(require_catalog_read)] = None,  # pylint: disable=unused-argument
) -> ParseCatalogResponse:
    """Parse a catalog from an uploaded JSON file.

    This endpoint accepts a catalog JSON file, validates its format and content,
    then processes it to generate the required output files. Requires a valid
    JWT token with 'catalog:read' scope.

    Args:
        job_id: The job identifier for the parsing operation.
        file: The uploaded JSON file containing catalog data.
        token_data: Validated token data from JWT (injected by dependency).

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
        )

        return ParseCatalogResponse(
            status=ParseCatalogStatus.SUCCESS,
            message=result.message,
            output_path=result.output_path,
        )

    except InvalidFileFormatError as e:
        logger.warning("Invalid file format: %s", file.filename)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    except InvalidJSONError as e:
        logger.warning("Invalid JSON content in file: %s", file.filename)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    except CatalogParseError as e:
        logger.error("Catalog parsing failed for file: %s", file.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e

    except Exception as e:
        logger.exception("Unexpected error processing file: %s", file.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from e
