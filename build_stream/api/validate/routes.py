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

"""FastAPI routes for validate stage operations."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from api.validate.dependencies import (
    get_validate_use_case,
    get_validate_correlation_id,
)
from api.dependencies import verify_token, require_job_write
from api.validate.schemas import (
    ValidateRequestSchema,
    ValidateResponseSchema,
    ValidateErrorResponse,
)
from api.logging_utils import log_secure_info
from core.jobs.exceptions import (
    InvalidStateTransitionError,
    JobNotFoundError,
    UpstreamStageNotCompletedError,
)
from core.jobs.value_objects import ClientId, CorrelationId, JobId
from core.validate.exceptions import (
    StageGuardViolationError,
    ValidateDomainError,
    ValidationExecutionError,
)
from orchestrator.validate.commands import ValidateCommand
from orchestrator.validate.use_cases import ValidateUseCase


router = APIRouter(prefix="/jobs", tags=["Validate"])


def _build_error_response(
    error_code: str,
    message: str,
    correlation_id: str,
) -> ValidateErrorResponse:
    return ValidateErrorResponse(
        error=error_code,
        message=message,
        correlation_id=correlation_id,
        timestamp=datetime.now(timezone.utc).isoformat() + "Z",
    )


@router.post(
    "/{job_id}/stages/validate",
    response_model=ValidateResponseSchema,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger validate stage (Molecule-based cluster verification)",
    description=(
        "Trigger the validate stage for a job. Submits Molecule-based "
        "infrastructure tests to the NFS queue for the Playbook Watcher. "
        "Requires restart stage to be completed."
    ),
    responses={
        202: {"description": "Stage accepted and queued", "model": ValidateResponseSchema},
        400: {"description": "Invalid request", "model": ValidateErrorResponse},
        401: {"description": "Unauthorized", "model": ValidateErrorResponse},
        404: {"description": "Job not found", "model": ValidateErrorResponse},
        409: {"description": "Stage already active", "model": ValidateErrorResponse},
        412: {"description": "Upstream stage not completed", "model": ValidateErrorResponse},
        500: {"description": "Internal error", "model": ValidateErrorResponse},
    },
)
def create_validate(
    job_id: str,
    request_body: ValidateRequestSchema,
    token_data: dict = Depends(verify_token),
    use_case: ValidateUseCase = Depends(get_validate_use_case),
    correlation_id: CorrelationId = Depends(get_validate_correlation_id),
    _: None = Depends(require_job_write),
) -> ValidateResponseSchema:
    """Trigger the validate stage for a job.

    Accepts the request synchronously and returns 202 Accepted.
    """
    client_id = ClientId(token_data["client_id"])

    log_secure_info(
        "info",
        f"Validate request: job_id={job_id}, "
        f"client_id={client_id.value}, "
        f"correlation_id={correlation_id.value}, "
        f"scenarios={request_body.scenario_names}, "
        f"suite={request_body.test_suite}, "
        f"timeout={request_body.timeout_minutes}",
        str(correlation_id.value),
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
        command = ValidateCommand(
            job_id=validated_job_id,
            client_id=client_id,
            correlation_id=correlation_id,
            scenario_names=request_body.scenario_names or ["all"],
            test_suite=request_body.test_suite or "",
            timeout_minutes=request_body.timeout_minutes or 120,
        )
        result = use_case.execute(command)

        return ValidateResponseSchema(
            job_id=result.job_id,
            stage=result.stage_name,
            status=result.status,
            submitted_at=result.submitted_at,
            correlation_id=result.correlation_id,
            attempt=result.attempt,
        )

    except JobNotFoundError as exc:
        log_secure_info('warning', f"Job not found: {job_id}")
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

    except UpstreamStageNotCompletedError as exc:
        log_secure_info(
            "warning",
            f"Invalid state transition for job {job_id}",
            str(correlation_id.value),
        )
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail=_build_error_response(
                "UPSTREAM_STAGE_NOT_COMPLETED",
                exc.message,
                correlation_id.value,
            ).model_dump(),
        ) from exc

    except StageGuardViolationError as exc:
        log_secure_info(
            "warning",
            f"Invalid state transition for job {job_id}",
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
        log_secure_info(
            "error",
            "Unexpected error creating validate stage",
            str(correlation_id.value),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_build_error_response(
                "INTERNAL_ERROR",
                "An unexpected error occurred",
                correlation_id.value,
            ).model_dump(),
        ) from exc
