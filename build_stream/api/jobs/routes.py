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

"""FastAPI routes for job lifecycle operations."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status

from core.jobs.exceptions import (
    IdempotencyConflictError,
    InvalidStateTransitionError,
    JobNotFoundError,
)
from core.jobs.repositories import AuditEventRepository
from core.jobs.value_objects import (
    ClientId,
    CorrelationId,
    IdempotencyKey,
    JobId,
    JobState,
)
from orchestrator.jobs.commands import CreateJobCommand
from orchestrator.jobs.use_cases import CreateJobUseCase

from api.dependencies import verify_token
from api.jobs.dependencies import (
    get_audit_repo,
    get_client_id,
    get_correlation_id,
    get_create_job_use_case,
    get_idempotency_key,
    get_job_repo,
    get_stage_repo,
)
from api.jobs.schemas import (
    CreateJobRequest,
    CreateJobResponse,
    ErrorResponse,
    GetJobResponse,
    StageResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def _map_job_state_to_api_state(internal_state: JobState) -> str:
    """Map internal job state to API response state."""
    state_mapping = {
        JobState.CREATED: "PENDING",
        JobState.IN_PROGRESS: "RUNNING",
        JobState.COMPLETED: "SUCCEEDED",
        JobState.FAILED: "FAILED",
        JobState.CANCELLED: "CLEANED",
    }
    return state_mapping.get(internal_state, "UNKNOWN")


def _build_error_response(
    error_code: str,
    message: str,
    correlation_id: str,
) -> ErrorResponse:
    return ErrorResponse(
        error=error_code,
        message=message,
        correlation_id=correlation_id,
        timestamp=datetime.now(timezone.utc).isoformat() + "Z",
    )


@router.post(
    "",
    response_model=CreateJobResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        200: {"description": "Idempotent replay", "model": CreateJobResponse},
        201: {"description": "Job created", "model": CreateJobResponse},
        400: {"description": "Invalid request", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        409: {"description": "Idempotency conflict", "model": ErrorResponse},
        422: {"description": "Validation error", "model": ErrorResponse},
        500: {"description": "Internal error", "model": ErrorResponse},
    },
)
async def create_job(
    request: CreateJobRequest,
    response: Response,
    client_id: ClientId = Depends(get_client_id),
    correlation_id: CorrelationId = Depends(get_correlation_id),
    idempotency_key: str = Depends(get_idempotency_key),
    use_case: CreateJobUseCase = Depends(get_create_job_use_case),
    stage_repo = Depends(get_stage_repo),
) -> CreateJobResponse:
    """Create a job, handling idempotency and domain errors."""
    # pylint: disable=too-many-arguments,too-many-positional-arguments
    logger.info(
        "Create job request: client_id=%s, correlation_id=%s, idempotency_key=%s",
        client_id.value,
        correlation_id.value,
        idempotency_key,
    )

    try:
        command = CreateJobCommand(
            client_id=client_id,
            request_client_id=request.client_id,
            client_name=request.client_name,
            correlation_id=correlation_id,
            idempotency_key=IdempotencyKey(idempotency_key),
        )
        result = use_case.execute(command)
        # Set status code based on whether job was newly created
        if result.is_new:
            response.status_code = status.HTTP_201_CREATED
        else:
            response.status_code = status.HTTP_200_OK
        stages_entities = stage_repo.find_all_by_job(JobId(result.job_id))  # pylint: disable=no-member
        stages = [
            StageResponse(
                stage_name=str(s.stage_name),
                stage_state=s.stage_state.value,
                started_at=s.started_at.isoformat() + "Z" if s.started_at else None,
                ended_at=s.ended_at.isoformat() + "Z" if s.ended_at else None,
                error_code=s.error_code,
                error_summary=s.error_summary,
            )
            for s in stages_entities
        ]
        return CreateJobResponse(
            job_id=result.job_id,
            correlation_id=correlation_id.value,
            job_state=result.job_state,
            created_at=result.created_at,
            stages=stages,
        )

    except IdempotencyConflictError as e:
        logger.warning("Idempotency conflict occurred")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_build_error_response(
                "IDEMPOTENCY_CONFLICT",
                e.message,
                correlation_id.value,
            ).model_dump(),
        ) from e

    except Exception as e:
        logger.exception("Unexpected error creating job")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_build_error_response(
                "INTERNAL_ERROR",
                "An unexpected error occurred",
                correlation_id.value,
            ).model_dump(),
        ) from e


@router.get(
    "/{job_id}",
    response_model=GetJobResponse,
    responses={
        200: {"description": "Job retrieved", "model": GetJobResponse},
        400: {"description": "Invalid job_id", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        404: {"description": "Job not found", "model": ErrorResponse},
        500: {"description": "Internal error", "model": ErrorResponse},
    },
)
async def get_job(
    job_id: str,
    token_data: dict = Depends(verify_token),
    client_id: ClientId = Depends(get_client_id),
    correlation_id: CorrelationId = Depends(get_correlation_id),
) -> GetJobResponse:
    """Return job status with state, timestamps, and step breakdown.
    
    Requires valid OAuth 2.0 token for authentication. Returns job state 
    (PENDING, RUNNING, SUCCEEDED, FAILED, CLEANED), timestamps for each 
    state change, and step breakdown with stage details.
    """
    logger.info(
        "Get job request: job_id=%s, client_id=%s, correlation_id=%s",
        job_id,
        client_id.value,
        correlation_id.value,
    )

    try:
        validated_job_id = JobId(job_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_build_error_response(
                "INVALID_JOB_ID",
                f"Invalid job_id format: {job_id}",
                correlation_id.value,
            ).model_dump(),
        ) from e

    job_repo = get_job_repo()
    stage_repo = get_stage_repo()
    audit_repo = get_audit_repo()

    try:
        job = job_repo.find_by_id(validated_job_id)  # pylint: disable=no-member
        if job is None or job.tombstoned:
            raise JobNotFoundError(job_id, correlation_id.value)

        if job.client_id != client_id:
            raise JobNotFoundError(job_id, correlation_id.value)

        # Get stage breakdown
        stages_entities = stage_repo.find_all_by_job(validated_job_id)  # pylint: disable=no-member
        stages = [
            StageResponse(
                stage_name=str(s.stage_name),
                stage_state=s.stage_state.value,
                started_at=s.started_at.isoformat() + "Z" if s.started_at else None,
                ended_at=s.ended_at.isoformat() + "Z" if s.ended_at else None,
                error_code=s.error_code,
                error_summary=s.error_summary,
            )
            for s in stages_entities
        ]
        
        # Get audit events for state change timestamps
        audit_events = audit_repo.find_by_job(validated_job_id)  # pylint: disable=no-member
        state_timestamps = {}
        for event in audit_events:
            if event.event_type.startswith("JOB_"):
                state_name = event.event_type.replace("JOB_", "")
                if state_name in ["CREATED", "IN_PROGRESS", "COMPLETED", "FAILED", "CANCELLED"]:
                    state_timestamps[state_name] = event.timestamp.isoformat() + "Z"
        
        # Always include creation timestamp
        if "CREATED" not in state_timestamps and job.created_at:
            state_timestamps["CREATED"] = job.created_at.isoformat() + "Z"
        
        return GetJobResponse(
            job_id=str(job.job_id),
            correlation_id=correlation_id.value,
            job_state=_map_job_state_to_api_state(job.job_state),
            created_at=job.created_at.isoformat() + "Z",
            updated_at=job.updated_at.isoformat() + "Z" if job.updated_at else None,
            tombstone=job.tombstoned,
            stages=stages,
            state_timestamps=state_timestamps if state_timestamps else None,
        )

    except JobNotFoundError as e:
        logger.warning("Job not found: %s", job_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_build_error_response(
                "JOB_NOT_FOUND",
                e.message,
                correlation_id.value,
            ).model_dump(),
        ) from e

    except Exception as e:
        logger.exception("Unexpected error retrieving job")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_build_error_response(
                "INTERNAL_ERROR",
                "An unexpected error occurred",
                correlation_id.value,
            ).model_dump(),
        ) from e


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Job deleted successfully"},
        400: {"description": "Invalid job_id", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        404: {"description": "Job not found", "model": ErrorResponse},
        500: {"description": "Internal error", "model": ErrorResponse},
    },
)
async def delete_job(
    job_id: str,
    client_id: ClientId = Depends(get_client_id),
    correlation_id: CorrelationId = Depends(get_correlation_id),
) -> None:
    """Delete (tombstone) a job for the requesting client if it exists."""
    logger.info(
        "Delete job request: job_id=%s, client_id=%s, correlation_id=%s",
        job_id,
        client_id.value,
        correlation_id.value,
    )

    try:
        validated_job_id = JobId(job_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_build_error_response(
                "INVALID_JOB_ID",
                f"Invalid job_id format: {job_id}",
                correlation_id.value,
            ).model_dump(),
        ) from e

    from api.jobs.dependencies import (  # pylint: disable=import-outside-toplevel
        get_job_repo as _get_job_repo,
        get_stage_repo as _get_stage_repo,
    )
    job_repo_instance = _get_job_repo()
    stage_repo_instance = _get_stage_repo()

    try:
        job = job_repo_instance.find_by_id(validated_job_id)  # pylint: disable=no-member
        if job is None:
            raise JobNotFoundError(job_id, correlation_id.value)

        if job.client_id != client_id:
            raise JobNotFoundError(job_id, correlation_id.value)

        job.tombstone()
        job_repo_instance.save(job)  # pylint: disable=no-member

        stages_entities = stage_repo_instance.find_all_by_job(validated_job_id)  # pylint: disable=no-member
        for stage in stages_entities:
            if not stage.stage_state.is_terminal():
                stage.cancel()
                stage_repo_instance.save(stage)  # pylint: disable=no-member

    except JobNotFoundError as e:
        logger.warning("Job not found: %s", job_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_build_error_response(
                "JOB_NOT_FOUND",
                e.message,
                correlation_id.value,
            ).model_dump(),
        ) from e

    except InvalidStateTransitionError as e:
        logger.warning("Invalid state transition occurred")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_build_error_response(
                "INVALID_STATE_TRANSITION",
                e.message,
                correlation_id.value,
            ).model_dump(),
        ) from e

    except Exception as e:
        logger.exception("Unexpected error deleting job")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_build_error_response(
                "INTERNAL_ERROR",
                "An unexpected error occurred",
                correlation_id.value,
            ).model_dump(),
        ) from e
