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

"""FastAPI routes for the (reintroduced, minimal) ParseCatalog stage.

Reintroduced in Omnia 2.3+ solely to catch the image_group_id
1:1-with-job uniqueness violation before create-local-repository/
build-image run (see orchestrator.catalog.use_cases.parse_catalog for
the full rationale). No file is uploaded here -- it reads the catalog
already uploaded via ``PUT /jobs/{job_id}/upload``.
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_correlation_id, require_job_write, verify_token
from api.logging_utils import log_secure_info
from api.parse_catalog.dependencies import get_parse_catalog_use_case
from api.parse_catalog.schemas import ParseCatalogErrorResponse, ParseCatalogResponse
from core.catalog.exceptions import CatalogNotUploadedError, InvalidCatalogFormatError
from core.image_group.exceptions import DuplicateImageGroupError
from core.jobs.exceptions import (
    InvalidStateTransitionError,
    JobNotFoundError,
    StageAlreadyCompletedError,
    TerminalStateViolationError,
)
from core.jobs.value_objects import ClientId, CorrelationId, JobId
from orchestrator.catalog.commands.parse_catalog import ParseCatalogCommand
from orchestrator.catalog.use_cases.parse_catalog import ParseCatalogUseCase

router = APIRouter(prefix="/jobs", tags=["Catalog Parsing"])


def _build_error_response(
    error_code: str, message: str, correlation_id: str
) -> ParseCatalogErrorResponse:
    return ParseCatalogErrorResponse(
        error=error_code,
        message=message,
        correlation_id=correlation_id,
        timestamp=datetime.now(timezone.utc).isoformat() + "Z",
    )


@router.post(
    "/{job_id}/stages/parse-catalog",
    response_model=ParseCatalogResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger parse-catalog stage",
    description=(
        "Reads the catalog already uploaded for this job (via PUT "
        "/jobs/{job_id}/upload) and checks that its image_group_id isn't "
        "already owned by another job's ImageGroup, before any "
        "create-local-repository/build-image cycles run. This is a "
        "synchronous, in-request check -- no playbook is invoked."
    ),
    responses={
        200: {"description": "Catalog parsed; image_group_id is unique", "model": ParseCatalogResponse},
        400: {"description": "Invalid request", "model": ParseCatalogErrorResponse},
        401: {"description": "Unauthorized", "model": ParseCatalogErrorResponse},
        404: {"description": "Job not found", "model": ParseCatalogErrorResponse},
        409: {"description": "State conflict or duplicate image_group_id", "model": ParseCatalogErrorResponse},
        412: {"description": "Precondition failed (job terminal or catalog not uploaded)", "model": ParseCatalogErrorResponse},
        500: {"description": "Internal error", "model": ParseCatalogErrorResponse},
    },
)
def parse_catalog(
    job_id: str,
    token_data: Annotated[dict, Depends(verify_token)] = None,  # pylint: disable=unused-argument
    use_case: ParseCatalogUseCase = Depends(get_parse_catalog_use_case),
    correlation_id: CorrelationId = Depends(get_correlation_id),
    _: None = Depends(require_job_write),
) -> ParseCatalogResponse:
    """Trigger the parse-catalog stage for a job.

    Synchronous: the uniqueness check completes within the request, so
    this returns 200 OK (not 202) on success.
    """
    client_id = ClientId(token_data["client_id"])

    log_secure_info(
        "info",
        f"Parse-catalog request: job_id={job_id}, correlation_id={correlation_id.value}",
        identifier=str(client_id.value),
        job_id=job_id,
    )

    try:
        validated_job_id = JobId(job_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_build_error_response(
                "INVALID_JOB_ID",
                f"Invalid job_id format: {job_id}",
                correlation_id.value,
            ).model_dump(),
        ) from exc

    try:
        command = ParseCatalogCommand(
            job_id=validated_job_id,
            client_id=client_id,
            correlation_id=correlation_id,
        )
        result = use_case.execute(command)

        log_secure_info(
            "info",
            f"Parse-catalog success: job_id={job_id}, "
            f"image_group_id={result.image_group_id}, status=200",
            job_id=job_id,
            end_section=True,
        )

        return ParseCatalogResponse(
            job_id=result.job_id,
            stage="parse-catalog",
            status=result.stage_state,
            image_group_id=result.image_group_id,
            message=result.message,
            correlation_id=correlation_id.value,
        )

    except JobNotFoundError as exc:
        log_secure_info(
            "warning",
            f"Parse-catalog failed: job_id={job_id}, reason=job_not_found, status=404",
            job_id=job_id,
            end_section=True,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_build_error_response(
                "JOB_NOT_FOUND", exc.message, correlation_id.value
            ).model_dump(),
        ) from exc

    except StageAlreadyCompletedError as exc:
        log_secure_info(
            "warning",
            f"Parse-catalog failed: job_id={job_id}, reason=stage_already_completed, status=409",
            job_id=job_id,
            end_section=True,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_build_error_response(
                "STAGE_ALREADY_COMPLETED", exc.message, correlation_id.value
            ).model_dump(),
        ) from exc

    except InvalidStateTransitionError as exc:
        log_secure_info(
            "warning",
            f"Parse-catalog failed: job_id={job_id}, reason=invalid_state_transition, status=409",
            job_id=job_id,
            end_section=True,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_build_error_response(
                "INVALID_STATE_TRANSITION", exc.message, correlation_id.value
            ).model_dump(),
        ) from exc

    except DuplicateImageGroupError as exc:
        log_secure_info(
            "warning",
            f"Parse-catalog failed: job_id={job_id}, reason=duplicate_image_group_id, status=409",
            job_id=job_id,
            end_section=True,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_build_error_response(
                "DUPLICATE_IMAGE_GROUP_ID", str(exc), correlation_id.value
            ).model_dump(),
        ) from exc

    except TerminalStateViolationError as exc:
        log_secure_info(
            "warning",
            f"Parse-catalog failed: job_id={job_id}, reason=terminal_state_violation, status=412",
            job_id=job_id,
            end_section=True,
        )
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail=_build_error_response(
                "PRECONDITION_FAILED", exc.message, correlation_id.value
            ).model_dump(),
        ) from exc

    except CatalogNotUploadedError as exc:
        log_secure_info(
            "warning",
            f"Parse-catalog failed: job_id={job_id}, reason=catalog_not_uploaded, status=412",
            job_id=job_id,
            end_section=True,
        )
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail=_build_error_response(
                "CATALOG_NOT_UPLOADED", exc.message, correlation_id.value
            ).model_dump(),
        ) from exc

    except InvalidCatalogFormatError as exc:
        log_secure_info(
            "warning",
            f"Parse-catalog failed: job_id={job_id}, reason=invalid_catalog_format, status=400",
            job_id=job_id,
            end_section=True,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_build_error_response(
                "INVALID_CATALOG_FORMAT", exc.message, correlation_id.value
            ).model_dump(),
        ) from exc

    except Exception as exc:
        log_secure_info(
            "error",
            f"Parse-catalog failed: job_id={job_id}, reason=unexpected_error, status=500",
            job_id=job_id,
            exc_info=True,
            end_section=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_build_error_response(
                "INTERNAL_ERROR", "An unexpected error occurred", correlation_id.value
            ).model_dump(),
        ) from exc
