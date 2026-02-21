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

"""FastAPI routes for OAuth2 authentication endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from api.logging_utils import log_secure_info
from api.vault_client import VaultError
from api.auth.schemas import (
    AuthErrorResponse,
    ClientRegistrationRequest,
    ClientRegistrationResponse,
    TokenRequest,
    TokenResponse,
)
from api.auth.service import (
    AuthService,
    AuthenticationError,
    ClientDisabledError,
    ClientExistsError,
    InvalidClientError,
    InvalidScopeError,
    MaxClientsReachedError,
    RegistrationDisabledError,
    TokenCreationError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

security = HTTPBasic()


def get_auth_service() -> AuthService:
    """Provide AuthService instance for dependency injection."""
    return AuthService()


def _verify_basic_auth(
    credentials: Annotated[HTTPBasicCredentials, Depends(security)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> HTTPBasicCredentials:
    """Verify Basic Authentication credentials for registration.

    Args:
        credentials: HTTP Basic Auth credentials from request.
        auth_service: AuthService instance.

    Returns:
        Validated credentials.

    Raises:
        HTTPException: If authentication fails.
    """
    try:
        auth_service.verify_registration_credentials(
            credentials.username,
            credentials.password,
        )
        return credentials
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_credentials",
                "error_description": "Invalid Basic Auth credentials",
            },
            headers={"WWW-Authenticate": "Basic"},
        ) from None
    except RegistrationDisabledError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "service_unavailable",
                "error_description": "Registration service is not available",
            },
        ) from None
    except Exception:
        logger.exception("Unexpected error during authentication")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "server_error",
                "error_description": "An unexpected error occurred",
            },
        ) from None


@router.post(
    "/register",
    response_model=ClientRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new OAuth client",
    description="Register a new OAuth client using HTTP Basic Authentication. "
    "Returns client_id and client_secret which must be securely stored.",
    responses={
        201: {
            "description": "Client registered successfully",
            "model": ClientRegistrationResponse,
        },
        400: {
            "description": "Invalid request (missing or malformed request body)",
            "model": AuthErrorResponse,
        },
        401: {
            "description": "Invalid Basic Auth credentials",
            "model": AuthErrorResponse,
        },
        409: {
            "description": "Client name already registered",
            "model": AuthErrorResponse,
        },
        422: {
            "description": "Validation error (invalid field values)",
            "model": AuthErrorResponse,
        },
        429: {
            "description": "Rate limit exceeded",
            "model": AuthErrorResponse,
        },
        500: {
            "description": "Internal server error",
            "model": AuthErrorResponse,
        },
        503: {
            "description": "Registration service unavailable",
            "model": AuthErrorResponse,
        },
    },
)
async def register_client(
    request: ClientRegistrationRequest,
    credentials: Annotated[HTTPBasicCredentials, Depends(_verify_basic_auth)],  # pylint: disable=unused-argument
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> ClientRegistrationResponse:
    """Register a new OAuth client.

    This endpoint requires HTTP Basic Authentication with pre-configured
    registration credentials. On success, returns client_id and client_secret
    which the client must securely store.

    **Important:** The client_secret is shown only once during registration.

    Args:
        request: Client registration request containing client_name and optional fields.
        credentials: Validated Basic Auth credentials (injected by dependency).
        auth_service: AuthService instance (injected by dependency).

    Returns:
        ClientRegistrationResponse with client_id and client_secret.

    Raises:
        HTTPException: With appropriate status code on failure.
    """
    logger.info("Client registration request received")

    try:
        registered_client = auth_service.register_client(
            client_name=request.client_name,
            description=request.description,
            allowed_scopes=request.allowed_scopes,
        )

        logger.info("Client registered successfully")

        return ClientRegistrationResponse(
            client_id=registered_client.client_id,
            client_secret=registered_client.client_secret,
            client_name=registered_client.client_name,
            allowed_scopes=registered_client.allowed_scopes,
            created_at=registered_client.created_at,
            expires_at=registered_client.expires_at,
        )

    except MaxClientsReachedError as e:
        log_secure_info("warning", "Client registration failed - max clients reached")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "max_clients_reached",
                "error_description": "Maximum number of clients (1) already registered"
            },
        ) from None
    except ClientExistsError:
        log_secure_info("warning", "Client registration failed - client exists")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "client_exists",
                "error_description": "Client with this name already exists",
            },
        ) from None
    except VaultError:
        log_secure_info("error", "Client registration failed - vault error", identifier=request.client_name)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "server_error",
                "error_description": "Failed to store client credentials",
            },
        ) from None
    except Exception as e:
        log_secure_info(
            "error",
            "Unexpected error during client registration"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "server_error",
                "error_description": "An unexpected error occurred",
            },
        ) from None


@router.post(
    "/token",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Request an access token",
    description="Exchange client credentials for a JWT access token using "
    "OAuth2 client_credentials grant type.",
    responses={
        200: {
            "description": "Token generated successfully",
            "model": TokenResponse,
        },
        400: {
            "description": "Invalid request (unsupported grant type, invalid scope)",
            "model": AuthErrorResponse,
        },
        401: {
            "description": "Invalid client credentials",
            "model": AuthErrorResponse,
        },
        403: {
            "description": "Client account is disabled",
            "model": AuthErrorResponse,
        },
        500: {
            "description": "Internal server error",
            "model": AuthErrorResponse,
        },
    },
)
async def request_token(
    request: Annotated[TokenRequest, Depends()],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Request an OAuth2 access token.

    This endpoint implements the OAuth2 client_credentials grant type.
    Clients must provide their client_id and client_secret to receive
    a JWT access token.

    Args:
        request: Token request containing grant_type, client_id, client_secret, and optional scope.
        auth_service: AuthService instance (injected by dependency).

    Returns:
        TokenResponse with access_token, token_type, expires_in, and scope.

    Raises:
        HTTPException: With appropriate status code on failure.
    """
    logger.info("Token request received")

    if request.client_id is None or request.client_secret is None:
        logger.warning("Token request missing client credentials")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_request",
                "error_description": "client_id and client_secret are required",
            },
        )

    try:
        token_result = auth_service.generate_token(
            client_id=request.client_id,
            client_secret=request.client_secret,
            requested_scope=request.scope,
        )

        logger.info("Token generated successfully")

        return TokenResponse(
            access_token=token_result.access_token,
            token_type=token_result.token_type,
            expires_in=token_result.expires_in,
            scope=token_result.scope,
        )

    except InvalidClientError:
        logger.warning("Token request failed - invalid client")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_client",
                "error_description": "Client authentication failed",
            },
        ) from None

    except ClientDisabledError:
        logger.warning("Token request failed - client disabled")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "client_disabled",
                "error_description": "Client account is disabled",
            },
        ) from None

    except InvalidScopeError as e:
        logger.warning("Token request failed - invalid scope")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_scope",
                "error_description": str(e),
            },
        ) from None

    except TokenCreationError:
        logger.error("Token request failed - token creation error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "server_error",
                "error_description": "Failed to create access token",
            },
        ) from None

    except Exception:
        logger.exception("Unexpected error during token request")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "server_error",
                "error_description": "An unexpected error occurred",
            },
        ) from None
