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

"""Mock implementation of VaultClient for testing."""

from typing import Any, Dict, Optional

from api.auth.password_handler import hash_password


class MockVaultClient:
    """In-memory mock implementation of VaultClient for testing.

    This mock provides the same interface as VaultClient but stores
    all data in memory, eliminating the need for Ansible Vault during tests.
    """

    DEFAULT_TEST_USERNAME = "test_registrar"
    DEFAULT_TEST_PASSWORD = "test_password"

    def __init__(
        self,
        auth_username: Optional[str] = None,
        auth_password: Optional[str] = None,
    ):
        """Initialize the mock vault client.

        Args:
            auth_username: Username for registration auth. Defaults to test_registrar.
            auth_password: Password for registration auth. Defaults to test_password.
        """
        username = auth_username or self.DEFAULT_TEST_USERNAME
        password = auth_password or self.DEFAULT_TEST_PASSWORD

        self._auth_config: Dict[str, Any] = {
            "auth_registration": {
                "username": username,
                "password_hash": hash_password(password),
            }
        }
        self._oauth_clients: Dict[str, Dict[str, Any]] = {}

    def get_auth_config(self) -> Dict[str, Any]:
        """Get authentication configuration.

        Returns:
            Auth configuration dictionary.
        """
        return self._auth_config

    def get_oauth_clients(self) -> Dict[str, Any]:
        """Get all registered OAuth clients.

        Returns:
            Dictionary of OAuth clients.
        """
        return self._oauth_clients.copy()

    def save_oauth_client(
        self,
        client_id: str,
        client_data: Dict[str, Any],
    ) -> None:
        """Save a new OAuth client.

        Args:
            client_id: The client identifier.
            client_data: Client data to store.
        """
        self._oauth_clients[client_id] = client_data

    def get_active_client_count(self) -> int:
        """Get the count of active registered clients.

        Returns:
            Number of active clients.
        """
        return sum(
            1 for c in self._oauth_clients.values()
            if c.get("is_active", True)
        )

    def client_exists(self, client_name: str) -> bool:
        """Check if a client with the given name already exists.

        Args:
            client_name: The client name to check.

        Returns:
            True if client exists, False otherwise.
        """
        for client_data in self._oauth_clients.values():
            if client_data.get("client_name") == client_name:
                return True
        return False

    def reset(self) -> None:
        """Reset the mock to initial state (clear all clients)."""
        self._oauth_clients.clear()

    def add_test_client(
        self,
        client_id: str = "bld_test_client_id",
        client_name: str = "test-client",
        is_active: bool = True,
    ) -> None:
        """Add a test client for testing scenarios.

        Args:
            client_id: Client ID to use.
            client_name: Client name to use.
            is_active: Whether the client is active.
        """
        self._oauth_clients[client_id] = {
            "client_name": client_name,
            "client_secret_hash": hash_password("test_secret"),
            "description": "Test client",
            "allowed_scopes": ["catalog:read"],
            "created_at": "2026-01-27T00:00:00Z",
            "is_active": is_active,
        }
