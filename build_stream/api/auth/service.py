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

"""Authentication service for OAuth2 client management."""

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from api.auth.jwt_handler import JWTHandler, JWTCreationError
from api.auth.password_handler import generate_credentials, verify_password
from api.logging_utils import log_auth_info
from api.vault_client import VaultClient, VaultDecryptError, VaultNotFoundError
from core.exceptions import (
    ClientDisabledError,
    InvalidClientError,
    InvalidScopeError,
    TokenCreationError,
)

DEFAULT_SCOPES = ["catalog:read"]


class AuthenticationError(Exception):
    """Exception raised when authentication fails."""


class ClientExistsError(Exception):
    """Exception raised when client name already exists."""


class MaxClientsReachedError(Exception):
    """Exception raised when maximum number of clients is already registered."""


class RegistrationDisabledError(Exception):
    """Exception raised when registration is disabled or misconfigured."""


@dataclass
class RegisteredClient:
    """Data class representing a registered OAuth client."""

    client_id: str
    client_secret: str
    client_name: str
    allowed_scopes: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None


@dataclass
class TokenResult:
    """Data class representing a token generation result."""

    access_token: str
    token_type: str
    expires_in: int
    scope: str


class AuthService:
    """Service for handling OAuth2 authentication operations."""

    def __init__(
        self,
        vault_client: Optional[VaultClient] = None,
        jwt_handler: Optional[JWTHandler] = None,
    ):
        """Initialize the authentication service.

        Args:
            vault_client: Optional VaultClient instance. Creates default if not provided.
            jwt_handler: Optional JWTHandler instance. Creates default if not provided.
        """
        self.vault_client = vault_client or VaultClient()
        self.jwt_handler = jwt_handler or JWTHandler()
        self._registration_username = os.getenv("AUTH_REGISTRATION_USERNAME")

    def verify_registration_credentials(self, username: str, password: str) -> bool:
        """Verify the Basic Auth credentials for registration endpoint.

        Args:
            username: The provided username.
            password: The provided password.

        Returns:
            True if credentials are valid.

        Raises:
            AuthenticationError: If credentials are invalid.
            RegistrationDisabledError: If registration is not configured.
        """
        try:
            auth_config = self.vault_client.get_auth_config()
        except VaultNotFoundError:
            raise RegistrationDisabledError(
                "Registration is not configured"
            ) from None
        except VaultDecryptError:
            raise RegistrationDisabledError(
                "Registration configuration error"
            ) from None

        registration_config = auth_config.get("auth_registration", {})
        stored_username = registration_config.get("username")
        stored_password_hash = registration_config.get("password_hash")

        if not stored_username or not stored_password_hash:
            raise RegistrationDisabledError(
                "Registration is not configured"
            ) from None

        if username != stored_username:
            raise AuthenticationError("Invalid credentials")

        if not verify_password(password, stored_password_hash):
            raise AuthenticationError("Invalid credentials")

        return True

    def register_client(
        self,
        client_name: str,
        description: Optional[str] = None,
        allowed_scopes: Optional[List[str]] = None,
    ) -> RegisteredClient:
        """Register a new OAuth client.

        Args:
            client_name: Unique name for the client.
            description: Optional description of the client.
            allowed_scopes: List of OAuth scopes to grant.

        Returns:
            RegisteredClient with credentials (secret shown only once).

        Raises:
            ClientExistsError: If client_name is already registered.
            MaxClientsReachedError: If maximum client limit (1) is reached.
            VaultError: If vault operations fail.
        """
        active_count = self.vault_client.get_active_client_count()
        if active_count >= 1:
            raise MaxClientsReachedError(
                "Maximum number of clients (1) already registered. "
                "Only one active client is supported."
            )

        if self.vault_client.client_exists(client_name):
            raise ClientExistsError("Client already exists")

        scopes = allowed_scopes if allowed_scopes else DEFAULT_SCOPES
        client_id, client_secret, hashed_secret = generate_credentials()
        created_at = datetime.now(timezone.utc)

        client_data = {
            "client_name": client_name,
            "client_secret_hash": hashed_secret,
            "description": description,
            "allowed_scopes": scopes,
            "created_at": created_at.isoformat(),
            "is_active": True,
        }

        self.vault_client.save_oauth_client(client_id, client_data)

        return RegisteredClient(
            client_id=client_id,
            client_secret=client_secret,
            client_name=client_name,
            allowed_scopes=scopes,
            created_at=created_at,
            expires_at=None,
        )

    def verify_client_credentials(
        self,
        client_id: str,
        client_secret: str,
    ) -> dict:
        """Verify client credentials for token endpoint.

        Args:
            client_id: The client identifier.
            client_secret: The client secret.

        Returns:
            Client data dictionary if credentials are valid.

        Raises:
            InvalidClientError: If client_id is unknown or secret is invalid.
            ClientDisabledError: If client account is disabled.
        """
        try:
            oauth_clients = self.vault_client.get_oauth_clients()
        except (VaultNotFoundError, VaultDecryptError):
            log_auth_info("error", "Failed to load OAuth clients from vault")
            # Ensure no exception details are exposed
            raise InvalidClientError("Client authentication failed") from None

        if client_id not in oauth_clients:
            log_auth_info("warning", f"Unknown client_id attempted authentication: {client_id}")
            raise InvalidClientError("Client authentication failed")

        client_data = oauth_clients[client_id]

        if not client_data.get("is_active", False):
            log_auth_info("warning", f"Disabled client attempted token request: {client_id}")
            raise ClientDisabledError("Client account is disabled")

        stored_hash = client_data.get("client_secret_hash")
        if not stored_hash or not verify_password(client_secret, stored_hash):
            log_auth_info("warning", f"Invalid client secret provided: {client_id}")
            raise InvalidClientError("Client authentication failed")

        log_auth_info("info", f"Client credentials verified successfully: {client_id}")
        return client_data

    def generate_token(
        self,
        client_id: str,
        client_secret: str,
        requested_scope: Optional[str] = None,
    ) -> TokenResult:
        """Generate a JWT access token for authenticated client.

        Args:
            client_id: The client identifier.
            client_secret: The client secret.
            requested_scope: Optional space-separated list of requested scopes.

        Returns:
            TokenResult with access token and metadata.

        Raises:
            InvalidClientError: If client credentials are invalid.
            ClientDisabledError: If client account is disabled.
            InvalidScopeError: If requested scope is not allowed.
            TokenCreationError: If token creation fails.
        """
        client_data = self.verify_client_credentials(client_id, client_secret)

        allowed_scopes = client_data.get("allowed_scopes", DEFAULT_SCOPES)
        client_name = client_data.get("client_name", "")

        if requested_scope:
            requested_scopes = requested_scope.split()
            for scope in requested_scopes:
                if scope not in allowed_scopes:
                    log_auth_info(
                        "warning",
                        f"Client requested unauthorized scope: {scope}, client_id={client_id}",
                    )
                    raise InvalidScopeError(f"Scope '{scope}' is not allowed for this client")
            granted_scopes = requested_scopes
        else:
            granted_scopes = allowed_scopes

        try:
            access_token, expires_in = self.jwt_handler.create_access_token(
                client_id=client_id,
                client_name=client_name,
                scopes=granted_scopes,
            )
        except JWTCreationError:
            log_auth_info("error", f"Failed to create access token: {client_id}")
            raise TokenCreationError("Failed to create access token") from None

        log_auth_info("info", f"Access token generated successfully: {client_id}")

        return TokenResult(
            access_token=access_token,
            token_type="Bearer",
            expires_in=expires_in,
            scope=" ".join(granted_scopes),
        )
