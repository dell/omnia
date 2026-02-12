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

"""FastAPI routes for local repository stage operations."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from api.local_repo.dependencies import (
    get_create_local_repo_use_case,
    get_local_repo_client_id,
    get_local_repo_correlation_id,
)
from api.local_repo.schemas import CreateLocalRepoResponse, LocalRepoErrorResponse
from api.logging_utils import log_secure_info
from core.jobs.exceptions import (
    InvalidStateTransitionError,
    JobNotFoundError,
)
from core.jobs.value_objects import ClientId, CorrelationId, JobId
from core.localrepo.exceptions import (
    InputDirectoryInvalidError,
    InputFilesMissingError,
    LocalRepoDomainError,
)
from orchestrator.local_repo.commands import CreateLocalRepoCommand
from orchestrator.local_repo.use_cases import CreateLocalRepoUseCase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Local Repository"])


def _build_error_response(
    error_code: str,
    message: str,
    correlation_id: str,
) -> LocalRepoErrorResponse:
    return LocalRepoErrorResponse(
        error=error_code,
        message=message,
        correlation_id=correlation_id,
        timestamp=datetime.now(timezone.utc).isoformat() + "Z",
    )


@router.post(
    "/{job_id}/stages/create-local-repository",
    response_model=CreateLocalRepoResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create local repository",
    description="Trigger the create-local-repository stage for a job",
    responses={
        202: {"description": "Stage accepted", "model": CreateLocalRepoResponse},
        400: {"description": "Invalid request", "model": LocalRepoErrorResponse},
        401: {"description": "Unauthorized", "model": LocalRepoErrorResponse},
        404: {"description": "Job not found", "model": LocalRepoErrorResponse},
        409: {"description": "Stage conflict", "model": LocalRepoErrorResponse},
        500: {"description": "Internal error", "model": LocalRepoErrorResponse},
    },
)
def create_local_repository(
    job_id: str,
    use_case: CreateLocalRepoUseCase = Depends(get_create_local_repo_use_case),
    client_id: ClientId = Depends(get_local_repo_client_id),
    correlation_id: CorrelationId = Depends(get_local_repo_correlation_id),
) -> CreateLocalRepoResponse:
    """Trigger the create-local-repository stage for a job.

    Accepts the request synchronously and returns 202 Accepted.
    The playbook execution is handled by the NFS queue watcher service.
    """
    logger.info(
        "Create local repo request: job_id=%s, client_id=%s, correlation_id=%s",
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
        command = CreateLocalRepoCommand(
            job_id=validated_job_id,
            client_id=client_id,
            correlation_id=correlation_id,
        )
        result = use_case.execute(command)

        return CreateLocalRepoResponse(
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

    except InputFilesMissingError as exc:
        log_secure_info(
            "warning",
            f"Input files missing for job {job_id}",
            str(correlation_id.value),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_build_error_response(
                "INPUT_FILES_MISSING",
                exc.message,
                correlation_id.value,
            ).model_dump(),
        ) from exc

    except InputDirectoryInvalidError as exc:
        log_secure_info(
            "warning",
            f"Input directory invalid for job {job_id}",
            str(correlation_id.value),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_build_error_response(
                "INPUT_DIRECTORY_INVALID",
                exc.message,
                correlation_id.value,
            ).model_dump(),
        ) from exc

    except LocalRepoDomainError as exc:
        log_secure_info(
            "error",
            f"Local repo domain error for job {job_id}",
            str(correlation_id.value),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_build_error_response(
                "LOCAL_REPO_ERROR",
                exc.message,
                correlation_id.value,
            ).model_dump(),
        ) from exc

    except Exception as exc:
        logger.exception("Unexpected error creating local repository stage")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_build_error_response(
                "INTERNAL_ERROR",
                "An unexpected error occurred",
                correlation_id.value,
            ).model_dump(),
        ) from exc
