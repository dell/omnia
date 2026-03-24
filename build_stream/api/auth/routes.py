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

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from api.logging_utils import log_auth_info
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
        log_auth_info("info", "Register auth: credentials verified")
        return credentials
    except AuthenticationError:
        log_auth_info("error", "Register auth: invalid credentials, status=401", end_section=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_credentials",
                "error_description": "Invalid Basic Auth credentials",
            },
            headers={"WWW-Authenticate": "Basic"},
        ) from None
    except RegistrationDisabledError:
        log_auth_info("warning", "Register auth: registration disabled, status=503", end_section=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "service_unavailable",
                "error_description": "Registration service is not available",
            },
        ) from None
    except Exception:
        log_auth_info("error", "Register auth: unexpected error during credential verification", exc_info=True, end_section=True)
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
    log_auth_info(
        "info",
        f"Register request: client_name={request.client_name}",
    )

    try:
        registered_client = auth_service.register_client(
            client_name=request.client_name,
            description=request.description,
            allowed_scopes=request.allowed_scopes,
        )

        log_auth_info(
            "info",
            f"Register success: client_name={request.client_name}, "
            f"client_id={registered_client.client_id}, "
            f"scopes={registered_client.allowed_scopes}, status=201",
            end_section=True,
        )

        return ClientRegistrationResponse(
            client_id=registered_client.client_id,
            client_secret=registered_client.client_secret,
            client_name=registered_client.client_name,
            allowed_scopes=registered_client.allowed_scopes,
            created_at=registered_client.created_at,
            expires_at=registered_client.expires_at,
        )

    except MaxClientsReachedError as e:
        log_auth_info("warning", f"Register failed: client_name={request.client_name}, reason=max_clients_reached, status=409", end_section=True)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "max_clients_reached",
                "error_description": "Maximum number of clients (1) already registered"
            },
        ) from None
    except ClientExistsError:
        log_auth_info("warning", f"Register failed: client_name={request.client_name}, reason=client_exists, status=409", end_section=True)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "client_exists",
                "error_description": "Client with this name already exists",
            },
        ) from None
    except VaultError:
        log_auth_info("error", f"Register failed: client_name={request.client_name}, reason=vault_error, status=500", end_section=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "server_error",
                "error_description": "Failed to store client credentials",
            },
        ) from None
    except Exception as e:
        log_auth_info(
            "error",
            f"Register failed: client_name={request.client_name}, reason=unexpected_error, status=500",
            exc_info=True,
            end_section=True,
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
    client_id_short = request.client_id if request.client_id else "None"
    log_auth_info(
        "info",
        f"Token request: client_id={client_id_short}, "
        f"grant_type={request.grant_type}, scope={request.scope}",
    )

    if request.client_id is None or request.client_secret is None:
        log_auth_info("warning", f"Token failed: client_id={client_id_short}, reason=missing_credentials, status=400", end_section=True)
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

        log_auth_info(
            "info",
            f"Token success: client_id={client_id_short}, "
            f"scope={token_result.scope}, "
            f"expires_in={token_result.expires_in}s, status=200",
            end_section=True,
        )

        return TokenResponse(
            access_token=token_result.access_token,
            token_type=token_result.token_type,
            expires_in=token_result.expires_in,
            scope=token_result.scope,
        )

    except InvalidClientError:
        log_auth_info("warning", f"Token failed: client_id={client_id_short}, reason=invalid_client, status=401", end_section=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "invalid_client",
                "error_description": "Client authentication failed",
            },
        ) from None

    except ClientDisabledError:
        log_auth_info("warning", f"Token failed: client_id={client_id_short}, reason=client_disabled, status=403", end_section=True)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "client_disabled",
                "error_description": "Client account is disabled",
            },
        ) from None

    except InvalidScopeError as e:
        log_auth_info("warning", f"Token failed: client_id={client_id_short}, reason=invalid_scope, detail={e}, status=400", end_section=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_scope",
                "error_description": str(e),
            },
        ) from None

    except TokenCreationError:
        log_auth_info("error", f"Token failed: client_id={client_id_short}, reason=token_creation_error, status=500", end_section=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "server_error",
                "error_description": "Failed to create access token",
            },
        ) from None

    except Exception:
        log_auth_info("error", f"Token failed: client_id={client_id_short}, reason=unexpected_error, status=500", exc_info=True, end_section=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "server_error",
                "error_description": "An unexpected error occurred",
            },
        ) from None
