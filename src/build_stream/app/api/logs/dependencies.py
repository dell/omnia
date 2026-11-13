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
# Applicable rules used: CG-AUTH-001.6, CG-AUTH-001.9, CG-SECRETS-001.1
# ****

"""FastAPI dependency providers for the pipeline log query API."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Iterator

from fastapi import Depends, HTTPException, status

from api.dependencies import get_job_repo, get_stage_repo, verify_token
from api.logging_utils import log_secure_info
from api.logs.limiter import (
    ConcurrencyLimiter,
    ConcurrencyLimitExceededError,
    RateLimitExceededError,
    SlidingWindowRateLimiter,
)
from common.config import LogQueryConfig, load_config
from core.logs.redaction import RedactionService
from infra.logs.filesystem_adapter import FileSystemLogAdapter
from orchestrator.logs.use_cases import (
    LogQuerySettings,
    LogQueryUseCase,
    StageLogMetadataService,
)


@lru_cache(maxsize=1)
def get_log_query_config() -> LogQueryConfig:
    """Load ``[log_query]`` from build_stream.ini, using defaults if unavailable."""
    try:
        return load_config().log_query
    except FileNotFoundError:
        log_secure_info("warning", "build_stream.ini not found; using log query defaults")
    except ValueError:
        log_secure_info(
            "error", "Invalid log query configuration; using safe defaults", exc_info=True
        )
    return LogQueryConfig()


@lru_cache(maxsize=1)
def get_log_file_service() -> FileSystemLogAdapter:
    """Provide the shared filesystem log adapter (keeps the line-count cache)."""
    return FileSystemLogAdapter(Path(get_log_query_config().log_root))


@lru_cache(maxsize=1)
def get_redaction_service() -> RedactionService:
    """Provide the shared redaction service."""
    return RedactionService()


@lru_cache(maxsize=1)
def get_rate_limiter() -> SlidingWindowRateLimiter:
    """Provide the per-client log query rate limiter."""
    return SlidingWindowRateLimiter(get_log_query_config().rate_limit_per_minute)


@lru_cache(maxsize=1)
def get_concurrency_limiter() -> ConcurrencyLimiter:
    """Provide the global log query concurrency limiter."""
    return ConcurrencyLimiter(get_log_query_config().max_concurrent)


def get_log_query_use_case(
    job_repo=Depends(get_job_repo),
    stage_repo=Depends(get_stage_repo),
    log_files: FileSystemLogAdapter = Depends(get_log_file_service),
    redaction: RedactionService = Depends(get_redaction_service),
    config: LogQueryConfig = Depends(get_log_query_config),
) -> LogQueryUseCase:
    """Provide the log query use case bound to request-scoped repositories."""
    return LogQueryUseCase(
        job_repo=job_repo,
        stage_repo=stage_repo,
        log_files=log_files,
        redaction=redaction,
        settings=LogQuerySettings(
            default_tail_lines=config.default_tail_lines,
            max_tail_lines=config.max_tail_lines,
            max_response_bytes=config.max_response_bytes,
        ),
    )


def get_stage_log_metadata_service(
    log_files: FileSystemLogAdapter = Depends(get_log_file_service),
) -> StageLogMetadataService:
    """Provide the stage log metadata service for GET /jobs/{job_id}."""
    return StageLogMetadataService(log_files)


def enforce_log_query_limits(
    token_data: Annotated[dict, Depends(verify_token)],
    rate_limiter: SlidingWindowRateLimiter = Depends(get_rate_limiter),
    concurrency: ConcurrencyLimiter = Depends(get_concurrency_limiter),
) -> Iterator[None]:
    """Apply the per-client rate limit and hold a concurrency slot for the request."""
    client_id = token_data["client_id"]
    try:
        rate_limiter.check(client_id)
    except RateLimitExceededError as exc:
        log_secure_info("warning", "Log query rate limit exceeded, status=429", client_id)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "RATE_LIMIT_EXCEEDED", "message": "Rate limit exceeded"},
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    try:
        with concurrency.slot():
            yield
    except ConcurrencyLimitExceededError as exc:
        log_secure_info("warning", "Log query concurrency limit reached, status=503", client_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "LOG_QUERY_BUSY",
                "message": "Log query capacity exhausted; retry later",
            },
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
