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

"""Common dependencies for API endpoints."""

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from api.auth.jwt_handler import (
    JWTExpiredError,
    JWTHandler,
    JWTInvalidSignatureError,
    JWTValidationError,
)
from api.logging_utils import log_secure_info

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

# Global JWT handler instance
_jwt_handler = JWTHandler()


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
