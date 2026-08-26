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

"""FastAPI routes for build image stage operations."""

from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, status

from api.build_image.dependencies import (
    get_create_build_image_use_case,
    get_build_image_correlation_id,
)
from api.dependencies import verify_token, require_job_write
from api.build_image.schemas import (
    CreateBuildImageRequest,
    CreateBuildImageResponse,
    BuildImageErrorResponse,
)
from api.logging_utils import log_secure_info
from core.build_image.exceptions import (
    BuildImageDomainError,
    InvalidArchitectureError,
    InvalidImageKeyError,
    InvalidFunctionalGroupsError,
    InventoryHostMissingError,
)
from core.jobs.exceptions import (
    InvalidStateTransitionError,
    JobNotFoundError,
    StageNotFoundError,
    TerminalStateViolationError,
    UpstreamStageNotCompletedError,
)
from core.jobs.value_objects import ClientId, CorrelationId, JobId
from orchestrator.build_image.commands import CreateBuildImageCommand
from orchestrator.build_image.use_cases import CreateBuildImageUseCase

router = APIRouter(prefix="/jobs", tags=["Build Image"])


def _build_error_response(
    error_code: str,
    message: str,
    correlation_id: str,
) -> BuildImageErrorResponse:
    return BuildImageErrorResponse(
        error=error_code,
        message=message,
        correlation_id=correlation_id,
        timestamp=datetime.now(timezone.utc).isoformat() + "Z",
    )


@router.post(
    "/{job_id}/stages/build-image",
    response_model=CreateBuildImageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create build image",
    description="Trigger the build-image stage for a job. "
                "Domain-segregated (Omnia 2.3+): Request body is optional. "
                "When omitted, the image_build_manager.yml playbook reads the catalog "
                "and builds all images for all architectures.",
    responses={
        202: {"description": "Stage accepted", "model": CreateBuildImageResponse},
        400: {"description": "Invalid request", "model": BuildImageErrorResponse},
        401: {"description": "Unauthorized", "model": BuildImageErrorResponse},
        404: {"description": "Job not found", "model": BuildImageErrorResponse},
        409: {"description": "Stage conflict", "model": BuildImageErrorResponse},
        500: {"description": "Internal error", "model": BuildImageErrorResponse},
    },
)
def create_build_image(
    job_id: str,
    request_body: Optional[CreateBuildImageRequest] = Body(None),
    token_data: Annotated[dict, Depends(verify_token)] = None,  # pylint: disable=unused-argument
    use_case: CreateBuildImageUseCase = Depends(get_create_build_image_use_case),
    correlation_id: CorrelationId = Depends(get_build_image_correlation_id),
    _: None = Depends(require_job_write),
) -> CreateBuildImageResponse:
    """Trigger the build-image stage for a job.

    Domain-segregated (Omnia 2.3+): Accepts empty request body. The playbook
    reads the catalog and builds all images for all architectures.

    Accepts the request synchronously and returns 202 Accepted.
    The playbook execution is handled by the NFS queue watcher service.
    """
    # Extract client_id from validated token data
    client_id = ClientId(token_data["client_id"])

    log_secure_info(
        "info",
        f"Create build image request: job_id={job_id}, "
        f"correlation_id={correlation_id.value}",
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
        # Handle None request_body (empty JSON body)
        if request_body is None:
            request_body = CreateBuildImageRequest()
        
        command = CreateBuildImageCommand(
            job_id=validated_job_id,
            client_id=client_id,
            correlation_id=correlation_id,
            architecture=request_body.architecture,
            image_key=request_body.image_key,
            functional_groups=request_body.functional_groups,
        )
        log_secure_info(
            "debug",
            f"Build image executing: job_id={job_id}",
            job_id=job_id,
        )
        result = use_case.execute(command)

        log_secure_info(
            "info",
            f"Build image success: job_id={job_id}, "
            f"stage={result.stage_name}, stage_status={result.status}, status=202",
            job_id=job_id,
            end_section=True,
        )

        return CreateBuildImageResponse(
            job_id=result.job_id,
            stage=result.stage_name,
            status=result.status,
            submitted_at=result.submitted_at,
            correlation_id=result.correlation_id,
            architecture=result.architecture,
            image_key=result.image_key,
            functional_groups=result.functional_groups,
        )

    except JobNotFoundError as exc:
        log_secure_info("warning", f"Build image failed: job_id={job_id}, reason=job_not_found, status=404", job_id=job_id, end_section=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_build_error_response(
                "JOB_NOT_FOUND",
                exc.message,
                correlation_id.value,
            ).model_dump(),
        ) from exc

    except StageNotFoundError as exc:
        log_secure_info("warning", f"Build image failed: job_id={job_id}, reason=stage_not_found, status=404", job_id=job_id, end_section=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_build_error_response(
                "STAGE_NOT_FOUND",
                exc.message,
                correlation_id.value,
            ).model_dump(),
        ) from exc

    except UpstreamStageNotCompletedError as exc:
        log_secure_info(
            "warning",
            f"Build image failed: job_id={job_id}, reason=upstream_stage_not_completed, status=412",
            job_id=job_id,
            end_section=True,
        )
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail=_build_error_response(
                "UPSTREAM_STAGE_NOT_COMPLETED",
                exc.message,
                correlation_id.value,
            ).model_dump(),
        ) from exc

    except InvalidStateTransitionError as exc:
        log_secure_info(
            "warning",
            f"Build image failed: job_id={job_id}, reason=invalid_state_transition, status=409",
            job_id=job_id,
            end_section=True,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_build_error_response(
                "INVALID_STATE_TRANSITION",
                exc.message,
                correlation_id.value,
            ).model_dump(),
        ) from exc

    except TerminalStateViolationError as exc:
        log_secure_info(
            "warning",
            f"Build image failed: job_id={job_id}, reason=terminal_state_violation, status=412",
            job_id=job_id,
            end_section=True,
        )
        if exc.state == "FAILED":
            message = f"Job {job_id} stage is in {exc.state} state and cannot be retried. Reset the stage using /stages/build-image/reset endpoint."
        else:
            message = f"Job {job_id} stage is in {exc.state} state and cannot be modified."

        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail=_build_error_response(
                "TERMINAL_STATE_VIOLATION",
                message,
                correlation_id.value,
            ).model_dump(),
        ) from exc

    except BuildImageDomainError as exc:
        log_secure_info(
            "error",
            f"Build image failed: job_id={job_id}, reason=domain_error, status=500",
            job_id=job_id,
            end_section=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_build_error_response(
                "BUILD_IMAGE_ERROR",
                exc.message,
                correlation_id.value,
            ).model_dump(),
        ) from exc

    except Exception as exc:
        error_detail = f"{type(exc).__name__}: {str(exc)}"
        log_secure_info(
            "error",
            f"Build image failed: job_id={job_id}, reason=unexpected_error, "
            f"error={error_detail}, status=500",
            job_id=job_id,
            exc_info=True,
            end_section=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_build_error_response(
                "INTERNAL_ERROR",
                f"An unexpected error occurred: {error_detail}",
                correlation_id.value,
            ).model_dump(),
        ) from exc
