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

"""FastAPI routes for restart stage operations."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.restart.dependencies import (
    get_create_restart_use_case,
    get_restart_correlation_id,
)
from api.dependencies import verify_token, require_job_write
from api.restart.schemas import (
    CreateRestartResponse,
    RestartErrorResponse,
    RestartLinksResponse,
)
from api.logging_utils import log_secure_info
from core.jobs.exceptions import (
    InvalidStateTransitionError,
    JobNotFoundError,
    StageNotFoundError,
    TerminalStateViolationError,
)
from core.jobs.value_objects import ClientId, CorrelationId, JobId
from orchestrator.restart.commands import CreateRestartCommand
from orchestrator.restart.use_cases import CreateRestartUseCase

router = APIRouter(prefix="/jobs", tags=["Restart"])


def _build_error_response(
    error_code: str,
    message: str,
    correlation_id: str,
) -> RestartErrorResponse:
    return RestartErrorResponse(
        error=error_code,
        message=message,
        correlation_id=correlation_id,
        timestamp=datetime.now(timezone.utc).isoformat() + "Z",
    )


@router.post(
    "/{job_id}/stages/restart",
    response_model=CreateRestartResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger restart stage",
    description=(
        "Triggers PXE-based node restart for the deployed Image Group. "
        "Executes utils/set_pxe_boot.yml via the playbook queue. "
        "Handles node diffs: only newly added nodes are PXE booted."
    ),
    responses={
        202: {"description": "Stage accepted", "model": CreateRestartResponse},
        400: {"description": "Invalid request", "model": RestartErrorResponse},
        401: {"description": "Unauthorized", "model": RestartErrorResponse},
        403: {"description": "Forbidden", "model": RestartErrorResponse},
        404: {"description": "Job not found", "model": RestartErrorResponse},
        409: {"description": "State conflict", "model": RestartErrorResponse},
        412: {"description": "Precondition failed", "model": RestartErrorResponse},
        500: {"description": "Internal error", "model": RestartErrorResponse},
    },
)
def create_restart(
    job_id: str,
    token_data: Annotated[dict, Depends(verify_token)] = None,  # pylint: disable=unused-argument
    use_case: CreateRestartUseCase = Depends(get_create_restart_use_case),
    correlation_id: CorrelationId = Depends(get_restart_correlation_id),
    _: None = Depends(require_job_write),
) -> CreateRestartResponse:
    """Trigger the restart stage for a job.

    Accepts the request synchronously and returns 202 Accepted.
    The playbook execution is handled by the NFS queue watcher service.
    """
    client_id = ClientId(token_data["client_id"])

    log_secure_info(
        "info",
        f"Create restart request: job_id={job_id}, "
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
        command = CreateRestartCommand(
            job_id=validated_job_id,
            client_id=client_id,
            correlation_id=correlation_id,
        )
        log_secure_info(
            "debug",
            f"Restart executing: job_id={job_id}",
            job_id=job_id,
        )
        result = use_case.execute(command)

        log_secure_info(
            "info",
            f"Restart success: job_id={job_id}, "
            f"stage={result.stage_name}, stage_status={result.status}, status=202",
            job_id=job_id,
            end_section=True,
        )

        return CreateRestartResponse(
            job_id=result.job_id,
            stage=result.stage_name,
            status=result.status,
            submitted_at=result.submitted_at,
            image_group_id=result.image_group_id,
            correlation_id=result.correlation_id,
            **{"_links": RestartLinksResponse(
                **{
                    "self": f"/api/v1/jobs/{result.job_id}",
                    "status": f"/api/v1/jobs/{result.job_id}",
                }
            )},
        )

    except JobNotFoundError as exc:
        log_secure_info("warning", f"Restart failed: job_id={job_id}, reason=job_not_found, status=404", job_id=job_id, end_section=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_build_error_response(
                "JOB_NOT_FOUND",
                exc.message,
                correlation_id.value,
            ).model_dump(),
        ) from exc

    except StageNotFoundError as exc:
        log_secure_info("warning", f"Restart failed: job_id={job_id}, reason=stage_not_found, status=404", job_id=job_id, end_section=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_build_error_response(
                "STAGE_NOT_FOUND",
                exc.message,
                correlation_id.value,
            ).model_dump(),
        ) from exc

    except InvalidStateTransitionError as exc:
        log_secure_info(
            "warning",
            f"Restart failed: job_id={job_id}, reason=invalid_state_transition, status=409",
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
            f"Restart failed: job_id={job_id}, reason=terminal_state_violation, status=412",
            job_id=job_id,
            end_section=True,
        )
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail=_build_error_response(
                "PRECONDITION_FAILED",
                exc.message,
                correlation_id.value,
            ).model_dump(),
        ) from exc

    except Exception as exc:
        log_secure_info(
            "error",
            f"Restart failed: job_id={job_id}, reason=unexpected_error, status=500",
            job_id=job_id,
            exc_info=True,
            end_section=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_build_error_response(
                "INTERNAL_ERROR",
                "An unexpected error occurred",
                correlation_id.value,
            ).model_dump(),
        ) from exc
