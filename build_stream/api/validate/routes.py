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

"""FastAPI routes for validate-image-on-test stage operations."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from api.validate.dependencies import (
    get_validate_image_on_test_use_case,
    get_validate_correlation_id,
)
from api.dependencies import verify_token, require_job_write
from api.validate.schemas import (
    ValidateImageOnTestResponse,
    ValidateImageOnTestErrorResponse,
)
from api.logging_utils import log_secure_info
from core.jobs.exceptions import (
    InvalidStateTransitionError,
    JobNotFoundError,
)
from core.jobs.value_objects import ClientId, CorrelationId, JobId
from core.validate.exceptions import (
    StageGuardViolationError,
    ValidateDomainError,
    ValidationExecutionError,
)
from orchestrator.validate.commands import ValidateImageOnTestCommand
from orchestrator.validate.use_cases import ValidateImageOnTestUseCase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Validate Image On Test"])


def _build_error_response(
    error_code: str,
    message: str,
    correlation_id: str,
) -> ValidateImageOnTestErrorResponse:
    return ValidateImageOnTestErrorResponse(
        error=error_code,
        message=message,
        correlation_id=correlation_id,
        timestamp=datetime.now(timezone.utc).isoformat() + "Z",
    )


@router.post(
    "/{job_id}/stages/validate-image-on-test",
    response_model=ValidateImageOnTestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Validate image on test environment",
    description="Trigger the validate-image-on-test stage for a job",
    responses={
        202: {"description": "Stage accepted", "model": ValidateImageOnTestResponse},
        400: {"description": "Invalid request", "model": ValidateImageOnTestErrorResponse},
        401: {"description": "Unauthorized", "model": ValidateImageOnTestErrorResponse},
        404: {"description": "Job not found", "model": ValidateImageOnTestErrorResponse},
        409: {"description": "Stage conflict", "model": ValidateImageOnTestErrorResponse},
        412: {"description": "Stage guard violation", "model": ValidateImageOnTestErrorResponse},
        500: {"description": "Internal error", "model": ValidateImageOnTestErrorResponse},
    },
)
def create_validate_image_on_test(
    job_id: str,
    token_data: dict = Depends(verify_token),
    use_case: ValidateImageOnTestUseCase = Depends(get_validate_image_on_test_use_case),
    correlation_id: CorrelationId = Depends(get_validate_correlation_id),
    _: None = Depends(require_job_write),
) -> ValidateImageOnTestResponse:
    """Trigger the validate-image-on-test stage for a job.

    Accepts the request synchronously and returns 202 Accepted.
    The playbook execution is handled by the NFS queue watcher service.
    """
    # Extract client_id from token_data
    client_id = token_data["client_id"]
    
    logger.info(
        "Validate image on test request: job_id=%s, client_id=%s, correlation_id=%s",
        job_id,
        client_id.value,
        correlation_id.value,
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
        command = ValidateImageOnTestCommand(
            job_id=validated_job_id,
            client_id=client_id,
            correlation_id=correlation_id,
        )
        result = use_case.execute(command)

        return ValidateImageOnTestResponse(
            job_id=result.job_id,
            stage=result.stage_name,
            status=result.status,
            submitted_at=result.submitted_at,
            correlation_id=result.correlation_id,
        )

    except JobNotFoundError as exc:
        logger.warning("Job not found: %s", job_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_build_error_response(
                "JOB_NOT_FOUND",
                exc.message,
                correlation_id.value,
            ).model_dump(),
        ) from exc

    except InvalidStateTransitionError as exc:
        log_secure_info(
            "warning",
            f"Invalid state transition for job {job_id}",
            str(correlation_id.value),
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_build_error_response(
                "INVALID_STATE_TRANSITION",
                exc.message,
                correlation_id.value,
            ).model_dump(),
        ) from exc

    except StageGuardViolationError as exc:
        log_secure_info(
            "warning",
            f"Stage guard violation for job {job_id}",
            str(correlation_id.value),
        )
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail=_build_error_response(
                "STAGE_GUARD_VIOLATION",
                exc.message,
                correlation_id.value,
            ).model_dump(),
        ) from exc

    except ValidationExecutionError as exc:
        log_secure_info(
            "error",
            f"Validation execution error for job {job_id}",
            str(correlation_id.value),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_build_error_response(
                "VALIDATION_EXECUTION_ERROR",
                exc.message,
                correlation_id.value,
            ).model_dump(),
        ) from exc

    except ValidateDomainError as exc:
        log_secure_info(
            "error",
            f"Validate domain error for job {job_id}",
            str(correlation_id.value),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_build_error_response(
                "VALIDATE_ERROR",
                exc.message,
                correlation_id.value,
            ).model_dump(),
        ) from exc

    except Exception as exc:
        logger.exception("Unexpected error creating validate-image-on-test stage")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_build_error_response(
                "INTERNAL_ERROR",
                "An unexpected error occurred",
                correlation_id.value,
            ).model_dump(),
        ) from exc
