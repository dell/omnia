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

# ****
# Secure code generated utilizing Code Guardian.
# Applicable rules used: CG-AUTH-001.2, CG-AUTH-001.9, CG-AUTH-001.6, CG-OUTPUT-001.1, CG-OUTPUT-001.2, CG-LOGGING-001.2
# ****

"""GET /api/v1/jobs/{job_id}/logs: redacted pipeline stage logs (ER-BSM-003 FR-2.1)."""

import time
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Annotated, NoReturn, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import get_correlation_id, verify_token
from api.jobs.schemas import ErrorResponse
from api.logging_utils import log_secure_info
from api.logs.dependencies import enforce_log_query_limits, get_log_query_use_case
from api.logs.schemas import JobLogsResponse, StageLogEntry
from core.jobs.exceptions import JobNotFoundError
from core.jobs.value_objects import ClientId, CorrelationId, JobId
from core.logs.exceptions import (
    InvalidLogQueryError,
    LogNotAvailableError,
    LogPathViolationError,
    LogUnavailableReason,
    StageNotFoundForJobError,
)
from orchestrator.logs.use_cases import LogQueryCommand, LogQueryUseCase

router = APIRouter(prefix="/jobs", tags=["Jobs"])

STAGE_PARAM_MAX_LENGTH = 64


def _raise(status_code: int, error: str, message: str, correlation_id: str) -> NoReturn:
    """Raise an HTTPException using the standard BSM error envelope."""
    raise HTTPException(
        status_code=status_code,
        detail=ErrorResponse(
            error=error,
            message=message,
            correlation_id=correlation_id,
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        ).model_dump(),
    )


@router.get(
    "/{job_id}/logs",
    response_model=JobLogsResponse,
    responses={
        200: {"description": "Redacted stage logs", "model": JobLogsResponse},
        400: {"description": "Invalid job_id or query parameters", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        404: {"description": "Job, stage, or stage log not found", "model": ErrorResponse},
        409: {"description": "Stored log path violation", "model": ErrorResponse},
        422: {"description": "Stage log is not readable text", "model": ErrorResponse},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal error", "model": ErrorResponse},
        503: {"description": "Log query capacity exhausted"},
    },
)
def get_job_logs(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    job_id: str,
    token_data: Annotated[dict, Depends(verify_token)],
    _limits: Annotated[None, Depends(enforce_log_query_limits)],
    stage: Annotated[
        Optional[str],
        Query(max_length=STAGE_PARAM_MAX_LENGTH, description="BSM stage name, e.g. build-image"),
    ] = None,
    tail_lines: Annotated[
        Optional[int], Query(description="Last N lines per stage (default from config)")
    ] = None,
    full: Annotated[
        bool, Query(description="Return the complete log, bounded by max_response_bytes")
    ] = False,
    correlation_id: CorrelationId = Depends(get_correlation_id),
    use_case: LogQueryUseCase = Depends(get_log_query_use_case),
) -> JobLogsResponse:
    """Return redacted Ansible execution logs for the stages of an owned job."""
    started = time.monotonic()
    corr = correlation_id.value
    client_id = ClientId(token_data["client_id"])

    try:
        validated_job_id = JobId(job_id)
    except ValueError:
        log_secure_info("warning", "Log query rejected: invalid job_id format, status=400")
        _raise(status.HTTP_400_BAD_REQUEST, "INVALID_JOB_ID", "Invalid job_id format", corr)

    job_ref = str(validated_job_id)
    command = LogQueryCommand(
        job_id=validated_job_id,
        client_id=client_id,
        correlation_id=corr,
        stage=stage,
        tail_lines=tail_lines,
        full=full,
    )
    query_desc = f"stage={stage or 'all'}, tail_lines={tail_lines}, full={full}"
    try:
        result = use_case.execute(command)
    except InvalidLogQueryError as exc:
        _audit(client_id, job_ref, query_desc, 400, started)
        _raise(status.HTTP_400_BAD_REQUEST, exc.error_code, exc.message, corr)
    except JobNotFoundError:
        _audit(client_id, job_ref, query_desc, 404, started)
        _raise(status.HTTP_404_NOT_FOUND, "JOB_NOT_FOUND", "Job not found", corr)
    except StageNotFoundForJobError as exc:
        _audit(client_id, job_ref, query_desc, 404, started)
        _raise(status.HTTP_404_NOT_FOUND, "STAGE_NOT_FOUND", exc.message, corr)
    except LogNotAvailableError as exc:
        if exc.reason == LogUnavailableReason.NOT_TEXT:
            _audit(client_id, job_ref, query_desc, 422, started)
            _raise(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "LOG_CONTENT_UNREADABLE", exc.message, corr
            )
        _audit(client_id, job_ref, query_desc, 404, started)
        _raise(status.HTTP_404_NOT_FOUND, "LOG_NOT_AVAILABLE", exc.message, corr)
    except LogPathViolationError as exc:
        _audit(client_id, job_ref, query_desc, 409, started)
        _raise(status.HTTP_409_CONFLICT, "LOG_PATH_VIOLATION", exc.message, corr)
    except Exception:  # pylint: disable=broad-exception-caught
        log_secure_info(
            "error", f"Log query failed: correlation_id={corr}, status=500",
            identifier=client_id.value, job_id=job_ref, exc_info=True,
        )
        _raise(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "INTERNAL_ERROR",
            "An unexpected error occurred", corr,
        )

    _audit(client_id, job_ref, query_desc, 200, started)
    return JobLogsResponse(
        job_id=result.job_id,
        correlation_id=corr,
        tail_lines=result.tail_lines,
        full=result.full,
        stages=[StageLogEntry(**asdict(entry)) for entry in result.stages],
    )


def _audit(
    client_id: ClientId, job_id: str, query_desc: str, status_code: int, started: float
) -> None:
    """Write the NFR-4 audit record for a log query."""
    duration_ms = int((time.monotonic() - started) * 1000)
    log_secure_info(
        "info" if status_code == 200 else "warning",
        f"Log query: job_id={job_id}, {query_desc}, status={status_code}, "
        f"duration_ms={duration_ms}",
        identifier=client_id.value,
        job_id=job_id,
        end_section=True,
    )
