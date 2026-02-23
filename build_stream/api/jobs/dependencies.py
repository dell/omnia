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

"""FastAPI dependency providers for Jobs API."""

from typing import Optional

from fastapi import Header, HTTPException, status

from core.jobs.value_objects import ClientId, CorrelationId
from infra.id_generator import JobUUIDGenerator
from infra.repositories import InMemoryJobRepository, InMemoryStageRepository
from orchestrator.jobs.use_cases import CreateJobUseCase


def _get_container():
    """Lazy import of container to avoid circular imports."""
    from container import container  # pylint: disable=import-outside-toplevel
    return container


def get_id_generator() -> JobUUIDGenerator:
    """Provide job ID generator."""
    return _get_container().job_id_generator()


def get_create_job_use_case() -> CreateJobUseCase:
    """Provide create job use case."""
    return _get_container().create_job_use_case()


def get_job_repo() -> InMemoryJobRepository:
    """Provide job repository."""
    return _get_container().job_repository()


def get_stage_repo() -> InMemoryStageRepository:
    """Provide stage repository."""
    return _get_container().stage_repository()


def get_audit_repo():
    """Provide audit event repository."""
    return _get_container().audit_repository()


def get_client_id(
    authorization: str = Header(..., description="Bearer token for authentication"),
) -> ClientId:
    """Extract ClientId from Bearer token header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )

    # Trim only the Bearer prefix and leading whitespace; preserve trailing
    # whitespace as part of token
    token = authorization[7:].lstrip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )

    # Implement real token validation and client_id extraction when auth is available.
    # For now, use token as client_id placeholder
    try:
        return ClientId(token[:128] if len(token) > 128 else token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client credentials",
        ) from e


def get_correlation_id(
    x_correlation_id: Optional[str] = Header(
        default=None,
        alias="X-Correlation-Id",
        description="Request tracing ID",
    ),
) -> CorrelationId:
    """Return provided correlation ID or generate one."""
    generator = _get_container().uuid_generator()
    if x_correlation_id:
        try:
            correlation_id = CorrelationId(x_correlation_id)
            return correlation_id
        except ValueError:
            pass

    generated_id = generator.generate()
    return CorrelationId(str(generated_id))


def get_idempotency_key(
    idempotency_key: str = Header(
        ...,
        alias="Idempotency-Key",
        description="Client-provided deduplication token",
    ),
) -> str:
    """Validate and return the Idempotency-Key header."""
    if idempotency_key is None or not idempotency_key.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Idempotency-Key must be provided",
        )

    key = idempotency_key.strip()

    if len(key) > 255:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Idempotency-Key length must be <= 255 characters",
        )

    return key
