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

"""Unit tests for AuthService."""

import pytest

from api.auth.service import (
    AuthenticationError,
    AuthService,
    ClientExistsError,
    MaxClientsReachedError,
)
from tests.mocks.mock_vault_client import MockVaultClient


@pytest.mark.unit
class TestAuthServiceCredentialVerification:
    """Test suite for AuthService.verify_registration_credentials."""

    def test_verify_valid_credentials(self, auth_service: AuthService):
        """Test verification with valid credentials."""
        result = auth_service.verify_registration_credentials(
            MockVaultClient.DEFAULT_TEST_USERNAME,
            MockVaultClient.DEFAULT_TEST_PASSWORD,
        )
        assert result is True

    def test_verify_invalid_username(self, auth_service: AuthService):
        """Test verification with invalid username."""
        with pytest.raises(AuthenticationError):
            auth_service.verify_registration_credentials(
                "wrong_username",
                MockVaultClient.DEFAULT_TEST_PASSWORD,
            )

    def test_verify_invalid_password(self, auth_service: AuthService):
        """Test verification with invalid password."""
        with pytest.raises(AuthenticationError):
            auth_service.verify_registration_credentials(
                MockVaultClient.DEFAULT_TEST_USERNAME,
                "wrong_password",
            )


@pytest.mark.unit
class TestAuthServiceClientRegistration:
    """Test suite for AuthService.register_client."""

    def test_register_client_success(self, auth_service: AuthService):
        """Test successful client registration."""
        result = auth_service.register_client(
            client_name="test-client",
            description="Test description",
            allowed_scopes=["catalog:read"],
        )

        assert result.client_id.startswith("bld_")
        assert result.client_secret.startswith("bld_s_")
        assert result.client_name == "test-client"
        assert result.allowed_scopes == ["catalog:read"]

    def test_register_client_default_scopes(self, auth_service: AuthService):
        """Test registration uses default scopes when not specified."""
        result = auth_service.register_client(client_name="test-client")

        assert result.allowed_scopes == ["catalog:read"]

    def test_register_client_max_clients_reached(
        self,
        mock_vault_client: MockVaultClient,
    ):
        """Test registration fails when max clients reached."""
        mock_vault_client.add_test_client()
        service = AuthService(vault_client=mock_vault_client)

        with pytest.raises(MaxClientsReachedError):
            service.register_client(client_name="new-client")

    def test_register_client_duplicate_name(self, auth_service: AuthService):
        """Test registration fails for duplicate client name."""
        auth_service.register_client(client_name="test-client")

        with pytest.raises((ClientExistsError, MaxClientsReachedError)):
            auth_service.register_client(client_name="test-client")
