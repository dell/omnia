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

"""FastAPI routes for catalog roles API."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import require_catalog_read, verify_token
from api.catalog_roles.dependencies import get_catalog_roles_service
from api.catalog_roles.schemas import ErrorResponse, GetRolesResponse
from api.logging_utils import log_secure_info
from api.catalog_roles.service import (
    CatalogRolesService,
    ParseCatalogNotCompletedError,
    RolesNotFoundError,
)
from core.jobs.exceptions import JobNotFoundError
from core.jobs.value_objects import JobId

router = APIRouter(prefix="/jobs", tags=["Catalog Roles"])


@router.get(
    "/{job_id}/catalog/roles",
    response_model=GetRolesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get catalog metadata including roles, image_key, and architectures",
    description=(
        "Returns catalog metadata extracted from parse-catalog artifacts: "
        "roles (from functional_layer.json), image_key (catalog Identifier), "
        "and supported architectures. This metadata is used by the build-image API. "
        "The parse-catalog stage must be in COMPLETED state before calling this endpoint. "
        "Requires a valid JWT token with 'catalog:read' scope."
    ),
    responses={
        200: {
            "description": "Roles retrieved successfully",
            "model": GetRolesResponse,
        },
        401: {
            "description": "Unauthorized (missing or invalid token)",
            "model": ErrorResponse,
        },
        403: {
            "description": "Forbidden (insufficient scope)",
            "model": ErrorResponse,
        },
        404: {
            "description": "Job not found or parse-catalog not yet completed",
            "model": ErrorResponse,
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
    },
)
async def get_catalog_roles(
    job_id: str,
    token_data: Annotated[dict, Depends(verify_token)] = None,  # pylint: disable=unused-argument
    scope_data: Annotated[dict, Depends(require_catalog_read)] = None,  # pylint: disable=unused-argument
    service: CatalogRolesService = Depends(get_catalog_roles_service),
) -> GetRolesResponse:
    """Return roles from the parse-catalog intermediate JSON for a given job.

    Args:
        job_id: The job identifier (UUID).
        token_data: Validated token data from JWT (injected by dependency).
        scope_data: Token data with validated 'catalog:read' scope (injected by dependency).

    Returns:
        GetRolesResponse containing the job_id and list of role names.

    Raises:
        HTTPException 400: If job_id is not a valid UUID format.
        HTTPException 401: If the Bearer token is missing or invalid.
        HTTPException 403: If the token lacks the required scope.
        HTTPException 404: If the job does not exist or parse-catalog has not completed.
        HTTPException 500: If an unexpected error occurs.
    """
    log_secure_info(
        "info",
        f"Get catalog roles request: job_id={job_id}",
        job_id=job_id,
    )

    try:
        validated_job_id = JobId(job_id)
    except ValueError as exc:
        log_secure_info(
            "warning",
            f"Get catalog roles failed: job_id={job_id}, reason=invalid_job_id,"
            f" detail={exc}, status=400",
            job_id=job_id,
            exc_info=True,
            end_section=True,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_JOB_ID",
                "message": f"Invalid job_id format: {job_id}",
            },
        ) from exc

    try:
        log_secure_info(
            "debug",
            f"Get catalog roles executing: job_id={job_id}",
            job_id=job_id,
        )
        result = service.get_roles(validated_job_id)
        log_secure_info(
            "info",
            f"Get catalog roles success: job_id={job_id}, status=200",
            job_id=job_id,
            end_section=True,
        )
        return GetRolesResponse(
            job_id=job_id,
            roles=result["roles"],
            image_key=result["image_key"],
            architectures=result["architectures"],
        )

    except ParseCatalogNotCompletedError as exc:
        log_secure_info(
            "warning",
            f"Get catalog roles failed: job_id={job_id},"
            f" reason=parse_catalog_not_completed, detail={exc}, status=404",
            job_id=job_id,
            exc_info=True,
            end_section=True,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "PARSE_CATALOG_NOT_COMPLETED",
                "message": str(exc),
            },
        ) from exc

    except RolesNotFoundError as exc:
        log_secure_info(
            "error",
            f"Get catalog roles failed: job_id={job_id},"
            f" reason=roles_not_found, detail={exc}, status=404",
            job_id=job_id,
            exc_info=True,
            end_section=True,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "ROLES_NOT_FOUND",
                "message": str(exc),
            },
        ) from exc

    except JobNotFoundError as exc:
        log_secure_info(
            "warning",
            f"Get catalog roles failed: job_id={job_id},"
            f" reason=job_not_found, detail={exc}, status=404",
            job_id=job_id,
            exc_info=True,
            end_section=True,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": "JOB_NOT_FOUND",
                "message": f"Job not found: {job_id}",
            },
        ) from exc

    except Exception as exc:
        log_secure_info(
            "error",
            f"Get catalog roles failed: job_id={job_id},"
            f" reason=unexpected_error, status=500",
            job_id=job_id,
            exc_info=True,
            end_section=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            },
        ) from exc
