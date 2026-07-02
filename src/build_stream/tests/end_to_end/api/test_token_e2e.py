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

"""End-to-end integration tests for the /api/v1/auth/token endpoint.

These tests run against a real FastAPI server with actual Ansible Vault,
providing true end-to-end validation of the token generation flow.

Usage:
    pytest tests/integration/test_token_e2e.py -v -m e2e

Requirements:
    - ansible-vault must be installed
    - Tests require write access to create temporary vault files
    - RSA keys must be available for JWT signing
"""

# pylint: disable=redefined-outer-name

from typing import Dict

import httpx
import pytest

# Import helper functions from conftest
from tests.end_to_end.api.conftest import (
    generate_test_client_secret,
    generate_invalid_client_id,
    generate_invalid_client_secret,
)


@pytest.fixture
def registered_client_e2e(  # noqa: W0613
        base_url: str,
        valid_auth_header: Dict[str, str],
        reset_vault: None,  # noqa: W0613 pylint: disable=unused-argument
    ) -> Dict[str, str]:
    """Register a client and return its credentials for token tests.

    Args:
        base_url: Server base URL.
        valid_auth_header: Valid Basic Auth header.
        reset_vault: Fixture to reset vault state.

    Returns:
        Dictionary with client_id and client_secret.
    """
    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        response = client.post(
            "/api/v1/auth/register",
            headers=valid_auth_header,
            json={
                "client_name": "token-e2e-client",
                "description": "E2E test client for token endpoint",
                "allowed_scopes": ["catalog:read", "catalog:write"],
            },
        )

    assert response.status_code == 201, f"Registration failed: {response.text}"

    data = response.json()
    return {
        "client_id": data["client_id"],
        "client_secret": data["client_secret"],
        "allowed_scopes": data["allowed_scopes"],
    }


@pytest.mark.e2e
@pytest.mark.integration
class TestTokenEndpointE2E:
    """End-to-end test suite for POST /api/v1/auth/token endpoint.

    These tests validate the complete token generation flow with real
    Ansible Vault and JWT signing.
    """

    TOKEN_URL = "/api/v1/auth/token"

    def test_token_valid_credentials_returns_200(
        self,
        base_url: str,
        registered_client_e2e: Dict[str, str],
    ):
        """Test successful token generation with valid credentials.

        Verifies the complete token flow:
        1. Client credentials verification against real encrypted vault
        2. JWT token generation with RS256 signing
        3. Response with access_token and metadata
        """
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": registered_client_e2e["client_id"],
                    "client_secret": registered_client_e2e["client_secret"],
                },
            )

        assert response.status_code == 200, f"Response: {response.text}"

        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] > 0
        assert "scope" in data

    def test_token_response_contains_all_fields(
        self,
        base_url: str,
        registered_client_e2e: Dict[str, str],
    ):
        """Test that token response contains all RFC 6749 required fields."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": registered_client_e2e["client_id"],
                    "client_secret": registered_client_e2e["client_secret"],
                },
            )

        assert response.status_code == 200, f"Response: {response.text}"

        data = response.json()
        expected_fields = ["access_token", "token_type", "expires_in", "scope"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"

    def test_token_jwt_structure(
        self,
        base_url: str,
        registered_client_e2e: Dict[str, str],
    ):
        """Test that access_token is a valid JWT with header.payload.signature."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": registered_client_e2e["client_id"],
                    "client_secret": registered_client_e2e["client_secret"],
                },
            )

        assert response.status_code == 200, f"Response: {response.text}"

        data = response.json()
        access_token = data["access_token"]

        # JWT should have 3 parts separated by dots
        parts = access_token.split(".")
        assert len(parts) == 3, "JWT should have header.payload.signature format"

        # Each part should be non-empty base64url encoded
        for i, part in enumerate(parts):
            assert len(part) > 0, f"JWT part {i} should not be empty"

    def test_token_with_valid_scope(
        self,
        base_url: str,
        registered_client_e2e: Dict[str, str],
    ):
        """Test token generation with valid requested scope."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": registered_client_e2e["client_id"],
                    "client_secret": registered_client_e2e["client_secret"],
                    "scope": "catalog:read",
                },
            )

        assert response.status_code == 200, f"Response: {response.text}"

        data = response.json()
        assert data["scope"] == "catalog:read"

    def test_token_with_multiple_scopes(
        self,
        base_url: str,
        registered_client_e2e: Dict[str, str],
    ):
        """Test token generation with multiple valid scopes."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": registered_client_e2e["client_id"],
                    "client_secret": registered_client_e2e["client_secret"],
                    "scope": "catalog:read catalog:write",
                },
            )

        assert response.status_code == 200, f"Response: {response.text}"

        data = response.json()
        assert "catalog:read" in data["scope"]
        assert "catalog:write" in data["scope"]

    def test_token_invalid_client_id_returns_401(
        self,
        base_url: str,
        registered_client_e2e: Dict[str, str],
    ):
        """Test token request with invalid client_id fails."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": "bld_invalid_client_id_12345678",
                    "client_secret": registered_client_e2e["client_secret"],
                },
            )

        assert response.status_code == 401, f"Response: {response.text}"

        data = response.json()
        assert data["detail"]["error"] == "invalid_client"

    def test_token_invalid_client_secret_returns_401(
        self,
        base_url: str,
        registered_client_e2e: Dict[str, str],
    ):
        """Test token request with invalid client_secret fails."""
        
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": registered_client_e2e["client_id"],
                    "client_secret": generate_test_client_secret(),
                },
            )

        assert response.status_code == 401, f"Response: {response.text}"

        data = response.json()
        assert data["detail"]["error"] == "invalid_client"

    def test_token_missing_client_id_returns_400(
        self,
        base_url: str,
        registered_client_e2e: Dict[str, str],
    ):
        """Test token request without client_id fails."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_secret": registered_client_e2e["client_secret"],
                },
            )

        assert response.status_code == 400, f"Response: {response.text}"

        data = response.json()
        assert data["detail"]["error"] == "invalid_request"

    def test_token_missing_client_secret_returns_400(
        self,
        base_url: str,
        registered_client_e2e: Dict[str, str],
    ):
        """Test token request without client_secret fails."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": registered_client_e2e["client_id"],
                },
            )

        assert response.status_code == 400, f"Response: {response.text}"

        data = response.json()
        assert data["detail"]["error"] == "invalid_request"

    def test_token_missing_grant_type_returns_422(
        self,
        base_url: str,
        registered_client_e2e: Dict[str, str],
    ):
        """Test token request without grant_type fails validation."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.TOKEN_URL,
                data={
                    "client_id": registered_client_e2e["client_id"],
                    "client_secret": registered_client_e2e["client_secret"],
                },
            )

        assert response.status_code == 422, f"Response: {response.text}"

    def test_token_invalid_grant_type_returns_422(
        self,
        base_url: str,
        registered_client_e2e: Dict[str, str],
    ):
        """Test token request with unsupported grant_type fails."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "password",
                    "client_id": registered_client_e2e["client_id"],
                    "client_secret": registered_client_e2e["client_secret"],
                },
            )

        assert response.status_code == 422, f"Response: {response.text}"

    def test_token_invalid_scope_returns_400(
        self,
        base_url: str,
        registered_client_e2e: Dict[str, str],
    ):
        """Test token request with unauthorized scope fails."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": registered_client_e2e["client_id"],
                    "client_secret": registered_client_e2e["client_secret"],
                    "scope": "admin:full",
                },
            )

        assert response.status_code == 400, f"Response: {response.text}"

        data = response.json()
        assert data["detail"]["error"] == "invalid_scope"

    def test_token_invalid_client_id_format_returns_422(
        self,
        base_url: str,
        registered_client_e2e: Dict[str, str],
    ):
        """Test token request with invalid client_id format fails."""
        
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": generate_invalid_client_id(),
                    "client_secret": registered_client_e2e["client_secret"],
                },
            )

        assert response.status_code == 422, f"Response: {response.text}"

    def test_token_invalid_client_secret_format_returns_422(
        self,
        base_url: str,
        registered_client_e2e: Dict[str, str],
    ):
        """Test token request with invalid client_secret format fails."""
        
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": registered_client_e2e["client_id"],
                    "client_secret": generate_invalid_client_secret(),
                },
            )

        assert response.status_code == 422, f"Response: {response.text}"

    def test_token_expires_in_is_positive(
        self,
        base_url: str,
        registered_client_e2e: Dict[str, str],
    ):
        """Test that expires_in is a positive integer."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": registered_client_e2e["client_id"],
                    "client_secret": registered_client_e2e["client_secret"],
                },
            )

        assert response.status_code == 200, f"Response: {response.text}"

        data = response.json()
        assert isinstance(data["expires_in"], int)
        assert data["expires_in"] > 0

    def test_token_type_is_bearer(
        self,
        base_url: str,
        registered_client_e2e: Dict[str, str],
    ):
        """Test that token_type is always 'Bearer'."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": registered_client_e2e["client_id"],
                    "client_secret": registered_client_e2e["client_secret"],
                },
            )

        assert response.status_code == 200, f"Response: {response.text}"

        data = response.json()
        assert data["token_type"] == "Bearer"

    def test_token_multiple_requests_return_different_tokens(
        self,
        base_url: str,
        registered_client_e2e: Dict[str, str],
    ):
        """Test that multiple token requests return different tokens (unique jti)."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response1 = client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": registered_client_e2e["client_id"],
                    "client_secret": registered_client_e2e["client_secret"],
                },
            )
            response2 = client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": registered_client_e2e["client_id"],
                    "client_secret": registered_client_e2e["client_secret"],
                },
            )

        assert response1.status_code == 200, f"Response1: {response1.text}"
        assert response2.status_code == 200, f"Response2: {response2.text}"

        token1 = response1.json()["access_token"]
        token2 = response2.json()["access_token"]

        # Tokens should be different (different jti)
        assert token1 != token2

    def test_token_default_scope_when_not_specified(
        self,
        base_url: str,
        registered_client_e2e: Dict[str, str],
    ):
        """Test that client's allowed scopes are used when scope not specified."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": registered_client_e2e["client_id"],
                    "client_secret": registered_client_e2e["client_secret"],
                },
            )

        assert response.status_code == 200, f"Response: {response.text}"

        data = response.json()
        # Should contain the client's allowed scopes
        for scope in registered_client_e2e["allowed_scopes"]:
            assert scope in data["scope"]
