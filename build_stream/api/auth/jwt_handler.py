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

"""JWT token generation and validation utilities.

This module provides JWT handling following the OAuth2 Implementation Spec:
- Algorithm: RS256 (RSA signature with SHA-256)
- Token Lifetime: 3600 seconds (1 hour)
- Claims: iss, sub, aud, iat, exp, nbf, jti, scope, client_name
"""

import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import jwt
from jwt.exceptions import (
    DecodeError,
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidSignatureError,
)

logger = logging.getLogger(__name__)


class JWTHandlerError(Exception):
    """Base exception for JWT operations."""


class JWTCreationError(JWTHandlerError):
    """Exception raised when JWT creation fails."""


class JWTValidationError(JWTHandlerError):
    """Exception raised when JWT validation fails."""


class JWTExpiredError(JWTValidationError):
    """Exception raised when JWT has expired."""


class JWTInvalidSignatureError(JWTValidationError):
    """Exception raised when JWT signature is invalid."""


@dataclass
class JWTConfig:
    """Configuration for JWT token handling."""

    private_key_path: str
    public_key_path: str
    algorithm: str = "RS256"
    access_token_expire_minutes: int = 60
    issuer: str = "build-stream-api"
    audience: str = "build-stream-api"
    key_id: str = "build-stream-key-2026-01"

    @classmethod
    def from_env(cls) -> "JWTConfig":
        """Create JWTConfig from environment variables."""
        return cls(
            private_key_path=os.getenv(
                "JWT_PRIVATE_KEY_PATH", "/etc/omnia/keys/jwt_private.pem"
            ),
            public_key_path=os.getenv(
                "JWT_PUBLIC_KEY_PATH", "/etc/omnia/keys/jwt_public.pem"
            ),
            algorithm=os.getenv("JWT_ALGORITHM", "RS256"),
            access_token_expire_minutes=int(
                os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
            ),
            issuer=os.getenv("JWT_ISSUER", "build-stream-api"),
            audience=os.getenv("JWT_AUDIENCE", "build-stream-api"),
            key_id=os.getenv("JWT_KEY_ID", "build-stream-key-2026-01"),
        )


@dataclass
class TokenData:
    """Data class representing decoded JWT token claims."""

    client_id: str
    client_name: str
    scopes: List[str]
    issued_at: datetime
    expires_at: datetime
    token_id: str


class JWTHandler:
    """Handler for JWT token creation and validation."""

    def __init__(self, config: Optional[JWTConfig] = None):
        """Initialize the JWT handler.

        Args:
            config: Optional JWTConfig instance. Creates from env if not provided.
        """
        self.config = config or JWTConfig.from_env()
        self._private_key: Optional[str] = None
        self._public_key: Optional[str] = None

    def _load_private_key(self) -> str:
        """Load the RSA private key for signing tokens.

        Returns:
            Private key as string.

        Raises:
            JWTCreationError: If key file cannot be read.
        """
        if self._private_key is None:
            try:
                with open(self.config.private_key_path, "r", encoding="utf-8") as f:
                    self._private_key = f.read()
            except FileNotFoundError:
                logger.error("JWT private key not found: %s", self.config.private_key_path)
                raise JWTCreationError(
                    f"JWT private key not found: {self.config.private_key_path}"
                ) from None
            except IOError:
                logger.error("Failed to read JWT private key")
                raise JWTCreationError("Failed to read JWT private key") from None
        return self._private_key

    def _load_public_key(self) -> str:
        """Load the RSA public key for verifying tokens.

        Returns:
            Public key as string.

        Raises:
            JWTValidationError: If key file cannot be read.
        """
        if self._public_key is None:
            try:
                with open(self.config.public_key_path, "r", encoding="utf-8") as f:
                    self._public_key = f.read()
            except FileNotFoundError:
                logger.error("JWT public key not found: %s", self.config.public_key_path)
                raise JWTValidationError(
                    f"JWT public key not found: {self.config.public_key_path}"
                ) from None
            except IOError:
                logger.error("Failed to read JWT public key")
                raise JWTValidationError("Failed to read JWT public key") from None
        return self._public_key

    def create_access_token(
        self,
        client_id: str,
        client_name: str,
        scopes: List[str],
    ) -> tuple[str, int]:
        """Create a JWT access token.

        Args:
            client_id: The client identifier (becomes 'sub' claim).
            client_name: Human-readable client name.
            scopes: List of granted scopes.

        Returns:
            Tuple of (access_token, expires_in_seconds).

        Raises:
            JWTCreationError: If token creation fails.
        """
        now = datetime.now(timezone.utc)
        expires_delta = timedelta(minutes=self.config.access_token_expire_minutes)
        expires_at = now + expires_delta
        token_id = str(uuid.uuid4())

        claims = {
            "iss": self.config.issuer,
            "sub": client_id,
            "aud": self.config.audience,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "nbf": int(now.timestamp()),
            "jti": token_id,
            "scope": " ".join(scopes),
            "client_name": client_name,
        }

        headers = {
            "alg": self.config.algorithm,
            "typ": "JWT",
            "kid": self.config.key_id,
        }

        try:
            private_key = self._load_private_key()
            token = jwt.encode(
                claims,
                private_key,
                algorithm=self.config.algorithm,
                headers=headers,
            )
            logger.info("Access token created for client: %s", client_id[:8] + "...")
            return token, int(expires_delta.total_seconds())
        except Exception:
            logger.error("Failed to create access token")
            raise JWTCreationError("Failed to create access token") from None

    def validate_token(self, token: str) -> TokenData:
        """Validate a JWT access token and extract claims.

        Args:
            token: The JWT token string.

        Returns:
            TokenData with decoded claims.

        Raises:
            JWTExpiredError: If token has expired.
            JWTInvalidSignatureError: If signature is invalid.
            JWTValidationError: If token is otherwise invalid.
        """
        try:
            public_key = self._load_public_key()
            payload = jwt.decode(
                token,
                public_key,
                algorithms=[self.config.algorithm],
                audience=self.config.audience,
                issuer=self.config.issuer,
            )

            return TokenData(
                client_id=payload["sub"],
                client_name=payload.get("client_name", ""),
                scopes=payload.get("scope", "").split(),
                issued_at=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
                expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
                token_id=payload.get("jti", ""),
            )
        except ExpiredSignatureError:
            logger.warning("Token has expired")
            raise JWTExpiredError("Token has expired") from None
        except (InvalidAudienceError, InvalidIssuerError):
            logger.warning("Invalid token claims")
            raise JWTValidationError("Invalid token claims") from None
        except InvalidSignatureError:
            logger.warning("Invalid token signature")
            raise JWTInvalidSignatureError("Invalid token signature") from None
        except DecodeError:
            logger.warning("Invalid token format")
            raise JWTValidationError("Invalid token format") from None
        except Exception:
            logger.error("Unexpected error validating token")
            raise JWTValidationError("Token validation failed") from None
