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

"""UAT tests for OAuth2 authentication flow."""

import base64
import uuid
import httpx
import pytest


@pytest.mark.uat
class TestClientRegistration:
    """Test OAuth2 client registration."""

    def test_register_client_with_valid_credentials(
        self, http_client: httpx.Client, auth_username: str, auth_password: str
    ):
        """Test client registration with valid credentials."""
        credentials = base64.b64encode(f"{auth_username}:{auth_password}".encode()).decode()
        headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "client_name": f"uat-test-{uuid.uuid4()}",
            "allowed_scopes": ["catalog:read", "catalog:write"],
        }
        
        response = http_client.post("/api/v1/auth/register", json=payload, headers=headers)
        
        # May be 201 (new) or 409 (already exists)
        assert response.status_code in [201, 409]
        if response.status_code == 201:
            data = response.json()
            assert "client_id" in data
            assert "client_secret" in data
            assert data["client_id"].startswith("bld_")
            assert data["client_secret"].startswith("bld_s_")

    def test_register_client_with_invalid_credentials_returns_401(
        self, http_client: httpx.Client
    ):
        """Test client registration with invalid credentials returns 401."""
        credentials = base64.b64encode(b"invalid:invalid").decode()
        headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "client_name": "test-client",
            "allowed_scopes": ["catalog:read"],
        }
        
        response = http_client.post("/api/v1/auth/register", json=payload, headers=headers)
        
        assert response.status_code == 401


@pytest.mark.uat
class TestTokenGeneration:
    """Test OAuth2 token generation."""

    def test_generate_token_with_valid_credentials(self, registered_client: dict):
        """Test token generation with valid client credentials."""
        assert "access_token" in registered_client
        assert "token_type" in registered_client
        assert registered_client["token_type"] == "Bearer"
        assert len(registered_client["access_token"]) > 0

    def test_token_contains_valid_structure(self, registered_client: dict):
        """Test generated token has valid JWT structure."""
        token = registered_client["access_token"]
        # JWT has 3 parts separated by dots
        parts = token.split('.')
        assert len(parts) == 3
        # Each part should be base64 encoded
        for part in parts:
            assert len(part) > 0
