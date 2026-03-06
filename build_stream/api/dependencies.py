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

"""Common dependencies for API endpoints.

This module provides all FastAPI dependencies including authentication,
authorization, database sessions, repositories, and domain-specific use cases.
"""

import logging
import os
from typing import Annotated, Generator

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from api.auth.jwt_handler import (
    JWTExpiredError,
    JWTHandler,
    JWTInvalidSignatureError,
    JWTValidationError,
)
from api.logging_utils import log_secure_info

logger = logging.getLogger(__name__)

# Environment configuration
_ENV = os.getenv("ENV", "prod")

# Authentication setup
security = HTTPBearer(auto_error=False)
_jwt_handler = JWTHandler()


def _get_container():
    """Lazy import of container to avoid circular imports."""
    from container import container  # pylint: disable=import-outside-toplevel
    return container


# ------------------------------------------------------------------
# Authentication & Authorization
# ------------------------------------------------------------------
def get_jwt_handler() -> JWTHandler:
    """Get the JWT handler instance.
    
    Returns:
        JWTHandler instance for token operations.
    """
    return _jwt_handler


def verify_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    jwt_handler: Annotated[JWTHandler, Depends(get_jwt_handler)],
) -> dict:
    """Verify JWT token from Authorization header.

    Args:
        credentials: HTTP Authorization credentials from request.
        jwt_handler: JWT handler instance.

    Returns:
        Token data dictionary with client information.

    Raises:
        HTTPException: If token is missing, invalid, or expired.
    """
    if credentials is None:
        logger.warning("Request missing Authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "missing_token",
                "error_description": "Authorization header is required",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        token_data = jwt_handler.validate_token(credentials.credentials)
        log_secure_info("info", "Token validated successfully", token_data.client_id)

        return {
            "client_id": token_data.client_id,
            "client_name": token_data.client_name,
            "scopes": token_data.scopes,
            "token_id": token_data.token_id,
        }

    except JWTExpiredError:
        logger.warning("Token validation failed - token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "token_expired",
                "error_description": "Access token has expired",
            },
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    except JWTInvalidSignatureError:
        logger.warning("Token validation failed - invalid signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_token",
                "error_description": "Invalid token signature",
            },
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    except JWTValidationError:
        logger.warning("Token validation failed: Invalid token format or content")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_token",
                "error_description": "Invalid access token",
            },
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


def require_scope(required_scope: str):
    """Create a dependency that requires a specific scope.

    Args:
        required_scope: The required scope (e.g., "catalog:read").

    Returns:
        Dependency function that validates the required scope.
    """
    def scope_dependency(
        token_data: Annotated[dict, Depends(verify_token)]
    ) -> dict:
        """Validate that the token has the required scope.

        Args:
            token_data: Token data from verify_token dependency.

        Returns:
            Token data if scope is valid.

        Raises:
            HTTPException: If required scope is not present.
        """
        if required_scope not in token_data["scopes"]:
            logger.warning(
                "Access denied - missing required scope: %s (client: %s)",
                required_scope,
                token_data["client_id"][:8] + "..."
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "insufficient_scope",
                    "error_description": f"Required scope '{required_scope}' is missing",
                },
            )

        logger.info(
            "Scope validation passed for client: %s, scope: %s",
            token_data["client_id"][:8] + "...",
            required_scope
        )
        return token_data

    return scope_dependency


# Common scope dependencies
require_catalog_read = require_scope("catalog:read")
require_catalog_write = require_scope("catalog:write")
require_job_write = require_scope("job:write")


# ------------------------------------------------------------------
# Database Session Management
# ------------------------------------------------------------------
def get_db_session() -> Generator[Session, None, None]:
    """Yield a single DB session per request for shared transaction context.
    
    In production, this creates a database session that is shared across
    all repositories within a single request, ensuring transactional consistency.
    In dev mode, returns None since in-memory repositories don't need sessions.
    """
    if _ENV != "prod":
        yield None  # type: ignore[misc]
        return
    
    from infra.db.session import SessionLocal  # pylint: disable=import-outside-toplevel
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ------------------------------------------------------------------
# Repository Factory Helpers
# ------------------------------------------------------------------
def _create_sql_job_repo(session: Session):
    """Create SQL job repository with session."""
    from infra.db.repositories import SqlJobRepository  # pylint: disable=import-outside-toplevel
    return SqlJobRepository(session=session)


def _create_sql_stage_repo(session: Session):
    """Create SQL stage repository with session."""
    from infra.db.repositories import SqlStageRepository  # pylint: disable=import-outside-toplevel
    return SqlStageRepository(session=session)


def _create_sql_idempotency_repo(session: Session):
    """Create SQL idempotency repository with session."""
    from infra.db.repositories import SqlIdempotencyRepository  # pylint: disable=import-outside-toplevel
    return SqlIdempotencyRepository(session=session)


def _create_sql_audit_repo(session: Session):
    """Create SQL audit event repository with session."""
    from infra.db.repositories import SqlAuditEventRepository  # pylint: disable=import-outside-toplevel
    return SqlAuditEventRepository(session=session)


# ------------------------------------------------------------------
# Repository Providers
# ------------------------------------------------------------------
def get_job_repo(db_session: Session = Depends(get_db_session)):
    """Provide job repository with shared session in prod."""
    if _ENV == "prod":
        return _create_sql_job_repo(db_session)
    return _get_container().job_repository()


def get_stage_repo(db_session: Session = Depends(get_db_session)):
    """Provide stage repository with shared session in prod."""
    if _ENV == "prod":
        return _create_sql_stage_repo(db_session)
    return _get_container().stage_repository()

def get_audit_repo(db_session: Session = Depends(get_db_session)):
    """Provide audit event repository."""
    if _ENV == "prod":
        return _create_sql_audit_repo(db_session)
    return _get_container().audit_repository()


# ------------------------------------------------------------------
# Job-Specific Dependencies
# ------------------------------------------------------------------
from core.jobs.value_objects import ClientId, CorrelationId
from infra.id_generator import JobUUIDGenerator
from orchestrator.jobs.use_cases import CreateJobUseCase


def get_id_generator() -> JobUUIDGenerator:
    """Provide job ID generator."""
    return _get_container().job_id_generator()


def get_client_id(token_data: dict) -> ClientId:
    """Extract ClientId from verified token data.
    
    Note: token_data comes from verify_token dependency injected in the route.
    This function is called after verify_token has already validated the JWT.
    
    Args:
        token_data: Token data dict from verify_token dependency.
        
    Returns:
        ClientId extracted from token.
    """
    return ClientId(token_data["client_id"])


def get_correlation_id(
    x_correlation_id: Annotated[str, Header(
        alias="X-Correlation-Id",
        description="Request tracing ID",
    )] = None,
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
    idempotency_key: Annotated[str, Header(
        alias="Idempotency-Key",
        description="Client-provided deduplication token",
    )] = None,
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


def get_create_job_use_case(
    db_session: Session = Depends(get_db_session),
) -> CreateJobUseCase:
    """Provide create-job use case with shared session in prod."""
    if _ENV == "prod":
        container = _get_container()
        return CreateJobUseCase(
            job_repo=_create_sql_job_repo(db_session),
            stage_repo=_create_sql_stage_repo(db_session),
            idempotency_repo=_create_sql_idempotency_repo(db_session),
            audit_repo=_create_sql_audit_repo(db_session),
            job_id_generator=container.job_id_generator(),
            uuid_generator=container.uuid_generator(),
        )
    return _get_container().create_job_use_case()
