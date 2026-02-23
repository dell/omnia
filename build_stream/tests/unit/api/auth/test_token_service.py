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

"""Unit tests for AuthService token generation functionality."""

# pylint: disable=redefined-outer-name

import pytest

from api.auth.service import (
    AuthService,
    ClientDisabledError,
    InvalidClientError,
    InvalidScopeError,
)
from tests.mocks.mock_jwt_handler import MockJWTHandler
from tests.mocks.mock_vault_client import MockVaultClient


@pytest.fixture
def mock_jwt_handler():
    """Create a MockJWTHandler for testing."""
    return MockJWTHandler()


@pytest.fixture
def mock_vault_with_active_client():
    """Create a MockVaultClient with an active registered client."""
    vault = MockVaultClient()
    vault.add_test_client(
        client_id="bld_1234567890abcdef1234567890abcdef",
        client_name="test-client",
        is_active=True,
    )
    return vault


@pytest.fixture
def mock_vault_with_disabled_client():
    """Create a MockVaultClient with a disabled registered client."""
    vault = MockVaultClient()
    vault.add_test_client(
        client_id="bld_1234567890abcdef1234567890abcdef",
        client_name="disabled-client",
        is_active=False,
    )
    return vault


@pytest.fixture
def test_client_id():
    """Return the test client ID."""
    return "bld_1234567890abcdef1234567890abcdef"


@pytest.fixture
def test_client_secret():
    """Return the test client secret (matches hash in mock)."""
    return "test_secret"


@pytest.mark.unit
class TestAuthServiceClientVerification:
    """Test suite for AuthService.verify_client_credentials."""

    def test_verify_valid_client_credentials(
        self,
        mock_vault_with_active_client: MockVaultClient,
        test_client_id: str,
        test_client_secret: str,
    ):
        """Test verification with valid client credentials."""
        service = AuthService(vault_client=mock_vault_with_active_client)

        result = service.verify_client_credentials(
            client_id=test_client_id,
            client_secret=test_client_secret,
        )

        assert result is not None
        assert result["client_name"] == "test-client"
        assert result["is_active"] is True

    def test_verify_invalid_client_id(
        self,
        mock_vault_with_active_client: MockVaultClient,
        test_client_secret: str,
    ):
        """Test verification with unknown client_id."""
        service = AuthService(vault_client=mock_vault_with_active_client)

        with pytest.raises(InvalidClientError):
            service.verify_client_credentials(
                client_id="bld_unknown_client_id_here_1234",
                client_secret=test_client_secret,
            )

    def test_verify_invalid_client_secret(
        self,
        mock_vault_with_active_client: MockVaultClient,
        test_client_id: str,
    ):
        """Test verification with invalid client_secret."""
        service = AuthService(vault_client=mock_vault_with_active_client)

        with pytest.raises(InvalidClientError):
            service.verify_client_credentials(
                client_id=test_client_id,
                client_secret="wrong_secret",
            )

    def test_verify_disabled_client(
        self,
        mock_vault_with_disabled_client: MockVaultClient,
        test_client_id: str,
        test_client_secret: str,
    ):
        """Test verification fails for disabled client."""
        service = AuthService(vault_client=mock_vault_with_disabled_client)

        with pytest.raises(ClientDisabledError):
            service.verify_client_credentials(
                client_id=test_client_id,
                client_secret=test_client_secret,
            )

    def test_verify_empty_vault(self, mock_vault_client: MockVaultClient):
        """Test verification fails when no clients registered."""
        service = AuthService(vault_client=mock_vault_client)

        with pytest.raises(InvalidClientError):
            service.verify_client_credentials(
                client_id="bld_any_client_id_here_12345678",
                client_secret="any_secret",
            )


@pytest.mark.unit
class TestAuthServiceTokenGeneration:
    """Test suite for AuthService.generate_token."""

    def test_generate_token_success(
        self,
        mock_vault_with_active_client: MockVaultClient,
        mock_jwt_handler: MockJWTHandler,
        test_client_id: str,
        test_client_secret: str,
    ):
        """Test successful token generation."""
        service = AuthService(
            vault_client=mock_vault_with_active_client,
            jwt_handler=mock_jwt_handler,
        )

        result = service.generate_token(
            client_id=test_client_id,
            client_secret=test_client_secret,
        )

        assert result is not None
        assert result.access_token is not None
        assert len(result.access_token) > 0
        assert result.token_type == "Bearer"
        assert result.expires_in > 0
        assert "catalog:read" in result.scope

    def test_generate_token_with_valid_scope(
        self,
        mock_vault_with_active_client: MockVaultClient,
        mock_jwt_handler: MockJWTHandler,
        test_client_id: str,
        test_client_secret: str,
    ):
        """Test token generation with valid requested scope."""
        service = AuthService(
            vault_client=mock_vault_with_active_client,
            jwt_handler=mock_jwt_handler,
        )

        result = service.generate_token(
            client_id=test_client_id,
            client_secret=test_client_secret,
            requested_scope="catalog:read",
        )

        assert result is not None
        assert result.scope == "catalog:read"

    def test_generate_token_with_invalid_scope(
        self,
        mock_vault_with_active_client: MockVaultClient,
        mock_jwt_handler: MockJWTHandler,
        test_client_id: str,
        test_client_secret: str,
    ):
        """Test token generation fails with unauthorized scope."""
        service = AuthService(
            vault_client=mock_vault_with_active_client,
            jwt_handler=mock_jwt_handler,
        )

        with pytest.raises(InvalidScopeError):
            service.generate_token(
                client_id=test_client_id,
                client_secret=test_client_secret,
                requested_scope="admin:full",
            )

    def test_generate_token_invalid_client(
        self,
        mock_vault_with_active_client: MockVaultClient,
        mock_jwt_handler: MockJWTHandler,
        test_client_secret: str,
    ):
        """Test token generation fails with invalid client."""
        service = AuthService(
            vault_client=mock_vault_with_active_client,
            jwt_handler=mock_jwt_handler,
        )

        with pytest.raises(InvalidClientError):
            service.generate_token(
                client_id="bld_invalid_client_id_12345678",
                client_secret=test_client_secret,
            )

    def test_generate_token_disabled_client(
        self,
        mock_vault_with_disabled_client: MockVaultClient,
        mock_jwt_handler: MockJWTHandler,
        test_client_id: str,
        test_client_secret: str,
    ):
        """Test token generation fails for disabled client."""
        service = AuthService(
            vault_client=mock_vault_with_disabled_client,
            jwt_handler=mock_jwt_handler,
        )

        with pytest.raises(ClientDisabledError):
            service.generate_token(
                client_id=test_client_id,
                client_secret=test_client_secret,
            )

    def test_generate_token_jwt_structure(
        self,
        mock_vault_with_active_client: MockVaultClient,
        mock_jwt_handler: MockJWTHandler,
        test_client_id: str,
        test_client_secret: str,
    ):
        """Test that generated token has valid JWT structure."""
        service = AuthService(
            vault_client=mock_vault_with_active_client,
            jwt_handler=mock_jwt_handler,
        )

        result = service.generate_token(
            client_id=test_client_id,
            client_secret=test_client_secret,
        )

        # JWT should have 3 parts separated by dots
        parts = result.access_token.split(".")
        assert len(parts) == 3, "JWT should have header.payload.signature format"

        # Each part should be non-empty
        for part in parts:
            assert len(part) > 0, "JWT parts should not be empty"
