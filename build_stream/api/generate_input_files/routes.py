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

"""FastAPI routes for GenerateInputFiles API."""

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, status

from api.dependencies import require_catalog_read, verify_token
from api.generate_input_files.dependencies import get_generate_input_files_use_case
from api.logging_utils import log_secure_info
from core.artifacts.exceptions import ArtifactNotFoundError
from core.artifacts.value_objects import SafePath
from core.catalog.exceptions import (
    AdapterPolicyValidationError,
    ConfigGenerationError,
)
from core.jobs.exceptions import (
    JobNotFoundError,
    StageAlreadyCompletedError,
    TerminalStateViolationError,
    UpstreamStageNotCompletedError,
)
from core.jobs.value_objects import CorrelationId, JobId
from orchestrator.catalog.commands.generate_input_files import (
    GenerateInputFilesCommand,
)
from orchestrator.catalog.use_cases import GenerateInputFilesUseCase

from api.generate_input_files.schemas import (
    ArtifactRefResponse,
    ErrorResponse,
    GenerateInputFilesRequest,
    GenerateInputFilesResponse,
)

router = APIRouter(prefix="/jobs", tags=["Input File Generation"])


@router.post(
    "/{job_id}/stages/generate-input-files",
    response_model=GenerateInputFilesResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate input files from parsed catalog",
    responses={
        400: {"description": "Invalid request", "model": ErrorResponse},
        404: {"description": "Job not found", "model": ErrorResponse},
        409: {"description": "Stage already completed", "model": ErrorResponse},
        422: {"description": "Upstream stage not completed", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def generate_input_files(
    job_id: str,
    request_body: Optional[GenerateInputFilesRequest] = Body(default=None),
    token_data: Annotated[dict, Depends(verify_token)] = None,  # pylint: disable=unused-argument
    scope_data: Annotated[dict, Depends(require_catalog_read)] = None,  # pylint: disable=unused-argument
    use_case: Annotated[GenerateInputFilesUseCase, Depends(get_generate_input_files_use_case)] = None,
) -> GenerateInputFilesResponse:
    """Generate Omnia input files from a parsed catalog.

    Args:
        job_id: The job identifier.
        request_body: Optional request with custom adapter policy path.
        token_data: Validated token data from JWT (injected by dependency).
        scope_data: Token data with validated scope (injected by dependency).

    Returns:
        GenerateInputFilesResponse with generated config details.
    """
    correlation_id = str(uuid.uuid4())

    adapter_path_str = (
        request_body.adapter_policy_path if request_body and request_body.adapter_policy_path else "default"
    )
    log_secure_info(
        "info",
        f"Generate-input-files request: job_id={job_id}, "
        f"adapter_policy={adapter_path_str}, correlation_id={correlation_id}",
        job_id=job_id,
    )

    try:
        validated_job_id = JobId(job_id)
    except ValueError as e:
        log_secure_info("error", f"Generate-input-files failed: job_id={job_id}, reason=invalid_job_id, status=400", job_id=job_id, end_section=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_JOB_ID", "message": str(e)},
        ) from e

    adapter_policy_path = None
    if request_body and request_body.adapter_policy_path:
        try:
            adapter_policy_path = SafePath.from_string(
                request_body.adapter_policy_path
            )
        except ValueError as e:
            log_secure_info("error", f"Generate-input-files failed: job_id={job_id}, reason=invalid_policy_path, status=400", job_id=job_id, end_section=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "INVALID_POLICY_PATH", "message": str(e)},
            ) from e

    command = GenerateInputFilesCommand(
        job_id=validated_job_id,
        correlation_id=CorrelationId(correlation_id),
        adapter_policy_path=adapter_policy_path,
    )

    try:
        result = use_case.execute(command)
        log_secure_info(
            "debug",
            f"Generate-input-files executing: job_id={job_id}, "
            f"adapter_policy={adapter_path_str}, correlation_id={correlation_id}",
            job_id=job_id,
        )

        log_secure_info(
            "info",
            f"Generate-input-files success: job_id={job_id}, "
            f"config_file_count={result.config_file_count}, stage_state={result.stage_state}, status=200",
            job_id=job_id,
            end_section=True,
        )

        return GenerateInputFilesResponse(
            job_id=result.job_id,
            stage_state=result.stage_state,
            message=result.message,
            configs_ref=ArtifactRefResponse(
                key=str(result.configs_ref.key),
                digest=str(result.configs_ref.digest),
                size_bytes=result.configs_ref.size_bytes,
                uri=result.configs_ref.uri,
            ),
            config_file_count=result.config_file_count,
            config_files=result.config_files,
            completed_at=result.completed_at,
        )

    except JobNotFoundError as e:
        log_secure_info("error", f"Generate-input-files failed: job_id={job_id}, reason=job_not_found, status=404", job_id=job_id, end_section=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "JOB_NOT_FOUND", "message": e.message},
        ) from e

    except TerminalStateViolationError as e:
        log_secure_info("error", f"Generate-input-files failed: job_id={job_id}, reason=terminal_state, status=409", job_id=job_id, end_section=True)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "TERMINAL_STATE", "message": e.message},
        ) from e

    except StageAlreadyCompletedError as e:
        log_secure_info("error", f"Generate-input-files failed: job_id={job_id}, reason=stage_already_completed, status=409", job_id=job_id, end_section=True)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "STAGE_ALREADY_COMPLETED", "message": e.message},
        ) from e

    except UpstreamStageNotCompletedError as e:
        log_secure_info("error", f"Generate-input-files failed: job_id={job_id}, reason=upstream_not_completed, status=422", job_id=job_id, end_section=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "UPSTREAM_STAGE_NOT_COMPLETED",
                "message": e.message,
            },
        ) from e

    except ArtifactNotFoundError as e:
        log_secure_info("error", f"Generate-input-files failed: job_id={job_id}, reason=upstream_artifact_not_found, status=422", job_id=job_id, end_section=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "UPSTREAM_ARTIFACT_NOT_FOUND",
                "message": e.message,
            },
        ) from e

    except (AdapterPolicyValidationError, ConfigGenerationError) as e:
        log_secure_info("error", f"Generate-input-files failed: job_id={job_id}, reason=config_generation_failed, status=500", job_id=job_id, end_section=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "CONFIG_GENERATION_FAILED", "message": e.message},
        ) from e

    except Exception as e:
        log_secure_info("error", f"Generate-input-files failed: job_id={job_id}, reason=unexpected_error, status=500", job_id=job_id, exc_info=True, end_section=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "INTERNAL_ERROR", "message": "An unexpected error occurred"},
        ) from e
