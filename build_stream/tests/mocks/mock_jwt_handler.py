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

"""Mock implementation of JWTHandler for testing."""

import base64
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import List

from api.auth.jwt_handler import TokenData


class MockJWTHandler:
    """In-memory mock implementation of JWTHandler for testing.

    This mock provides the same interface as JWTHandler but creates
    simple mock tokens without requiring actual RSA keys.
    """

    DEFAULT_EXPIRE_MINUTES = 60
    DEFAULT_ISSUER = "build-stream-api"
    DEFAULT_AUDIENCE = "build-stream-api"

    def __init__(
        self,
        access_token_expire_minutes: int = DEFAULT_EXPIRE_MINUTES,
        issuer: str = DEFAULT_ISSUER,
        audience: str = DEFAULT_AUDIENCE,
    ):
        """Initialize the mock JWT handler.

        Args:
            access_token_expire_minutes: Token expiration time in minutes.
            issuer: Token issuer claim.
            audience: Token audience claim.
        """
        self.access_token_expire_minutes = access_token_expire_minutes
        self.issuer = issuer
        self.audience = audience
        self._tokens: dict = {}

    def create_access_token(
        self,
        client_id: str,
        client_name: str,
        scopes: List[str],
    ) -> tuple[str, int]:
        """Create a mock JWT access token.

        Args:
            client_id: The client identifier (becomes 'sub' claim).
            client_name: Human-readable client name.
            scopes: List of granted scopes.

        Returns:
            Tuple of (access_token, expires_in_seconds).
        """
        now = datetime.now(timezone.utc)
        expires_delta = timedelta(minutes=self.access_token_expire_minutes)
        expires_at = now + expires_delta
        token_id = str(uuid.uuid4())

        # Create mock JWT structure (header.payload.signature)
        header = {
            "alg": "RS256",
            "typ": "JWT",
            "kid": "mock-key-id",
        }
        payload = {
            "iss": self.issuer,
            "sub": client_id,
            "aud": self.audience,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "nbf": int(now.timestamp()),
            "jti": token_id,
            "scope": " ".join(scopes),
            "client_name": client_name,
        }

        # Create base64url encoded parts
        header_b64 = base64.urlsafe_b64encode(
            json.dumps(header).encode()
        ).decode().rstrip("=")
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode().rstrip("=")
        # Mock signature
        signature_b64 = base64.urlsafe_b64encode(
            f"mock_signature_{token_id}".encode()
        ).decode().rstrip("=")

        token = f"{header_b64}.{payload_b64}.{signature_b64}"

        # Store token for validation
        self._tokens[token] = {
            "payload": payload,
            "client_id": client_id,
            "client_name": client_name,
            "scopes": scopes,
            "issued_at": now,
            "expires_at": expires_at,
            "token_id": token_id,
        }

        return token, int(expires_delta.total_seconds())

    def validate_token(self, token: str) -> TokenData:
        """Validate a mock JWT access token and extract claims.

        Args:
            token: The JWT token string.

        Returns:
            TokenData with decoded claims.

        Raises:
            ValueError: If token is invalid or not found.
        """
        if token not in self._tokens:
            raise ValueError("Invalid token")

        token_data = self._tokens[token]

        if datetime.now(timezone.utc) > token_data["expires_at"]:
            raise ValueError("Token has expired")

        return TokenData(
            client_id=token_data["client_id"],
            client_name=token_data["client_name"],
            scopes=token_data["scopes"],
            issued_at=token_data["issued_at"],
            expires_at=token_data["expires_at"],
            token_id=token_data["token_id"],
        )

    def reset(self) -> None:
        """Reset the mock to initial state (clear all tokens)."""
        self._tokens.clear()
