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

"""FastAPI dependency providers for Local Repository API."""

from typing import Optional

from fastapi import Header, HTTPException, status

from core.jobs.value_objects import ClientId, CorrelationId


def _get_container():
    """Lazy import of container to avoid circular imports."""
    from container import container  # pylint: disable=import-outside-toplevel
    return container


def get_create_local_repo_use_case():
    """Provide create local repo use case."""
    return _get_container().create_local_repo_use_case()


def get_local_repo_client_id(
    authorization: str = Header(..., description="Bearer token for authentication"),
) -> ClientId:
    """Extract ClientId from Bearer token header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )

    token = authorization[7:].lstrip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )

    try:
        return ClientId(token[:128] if len(token) > 128 else token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client credentials",
        ) from exc


def get_local_repo_correlation_id(
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
            return CorrelationId(x_correlation_id)
        except ValueError:
            pass

    generated_id = generator.generate()
    return CorrelationId(str(generated_id))
