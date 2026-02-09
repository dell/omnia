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

"""Integration tests for the /api/v1/auth/token endpoint."""

# pylint: disable=redefined-outer-name

from typing import Dict, Generator  # noqa: W0611 pylint: disable=unused-import

import pytest
from fastapi import status
from fastapi.testclient import TestClient


@pytest.fixture
def registered_client(test_client: TestClient, valid_auth_header: Dict[str, str]) -> Dict:
    """Register a client and return its credentials.

    Args:
        test_client: FastAPI test client.
        valid_auth_header: Valid Basic Auth header.

    Returns:
        Dictionary with client_id and client_secret.
    """
    response = test_client.post(
        "/api/v1/auth/register",
        headers=valid_auth_header,
        json={"client_name": "token-test-client"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    return {
        "client_id": data["client_id"],
        "client_secret": data["client_secret"],
        "allowed_scopes": data["allowed_scopes"],
    }


@pytest.fixture
def valid_token_request(registered_client: Dict) -> Dict:
    """Create a valid token request body.

    Args:
        registered_client: Registered client credentials.

    Returns:
        Dictionary with valid token request data.
    """
    return {
        "grant_type": "client_credentials",
        "client_id": registered_client["client_id"],
        "client_secret": registered_client["client_secret"],
    }


@pytest.mark.integration
class TestTokenEndpoint:
    """Test suite for POST /api/v1/auth/token endpoint."""

    TOKEN_URL = "/api/v1/auth/token"

    def test_token_valid_credentials_returns_200(
        self,
        test_client: TestClient,
        registered_client: Dict,
    ):
        """Test successful token generation with valid credentials."""
        response = test_client.post(
            self.TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": registered_client["client_id"],
                "client_secret": registered_client["client_secret"],
            },
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] > 0
        assert "scope" in data

    def test_token_response_contains_all_fields(
        self,
        test_client: TestClient,
        registered_client: Dict,
    ):
        """Test that token response contains all required fields."""
        response = test_client.post(
            self.TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": registered_client["client_id"],
                "client_secret": registered_client["client_secret"],
            },
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        expected_fields = ["access_token", "token_type", "expires_in", "scope"]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"

    def test_token_jwt_format(
        self,
        test_client: TestClient,
        registered_client: Dict,
    ):
        """Test that access_token is a valid JWT format."""
        response = test_client.post(
            self.TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": registered_client["client_id"],
                "client_secret": registered_client["client_secret"],
            },
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        access_token = data["access_token"]

        # JWT should have 3 parts separated by dots
        parts = access_token.split(".")
        assert len(parts) == 3, "JWT should have header.payload.signature format"

    def test_token_with_valid_scope(
        self,
        test_client: TestClient,
        registered_client: Dict,
    ):
        """Test token generation with valid requested scope."""
        response = test_client.post(
            self.TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": registered_client["client_id"],
                "client_secret": registered_client["client_secret"],
                "scope": "catalog:read",
            },
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["scope"] == "catalog:read"

    def test_token_invalid_client_id_returns_401(
        self,
        test_client: TestClient,
        registered_client: Dict,
    ):
        """Test token request with invalid client_id."""
        response = test_client.post(
            self.TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": "bld_invalid_client_id_12345678",
                "client_secret": registered_client["client_secret"],
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        data = response.json()
        assert data["detail"]["error"] == "invalid_client"

    def test_token_invalid_client_secret_returns_401(
        self,
        test_client: TestClient,
        registered_client: Dict,
    ):
        """Test token request with invalid client_secret."""
        from tests.conftest import generate_test_client_secret
        
        response = test_client.post(
            self.TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": registered_client["client_id"],
                "client_secret": generate_test_client_secret(),
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        data = response.json()
        assert data["detail"]["error"] == "invalid_client"

    def test_token_missing_client_id_returns_400(
        self,
        test_client: TestClient,
        registered_client: Dict,
    ):
        """Test token request without client_id."""
        response = test_client.post(
            self.TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_secret": registered_client["client_secret"],
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        data = response.json()
        assert data["detail"]["error"] == "invalid_request"

    def test_token_missing_client_secret_returns_400(
        self,
        test_client: TestClient,
        registered_client: Dict,
    ):
        """Test token request without client_secret."""
        response = test_client.post(
            self.TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": registered_client["client_id"],
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        data = response.json()
        assert data["detail"]["error"] == "invalid_request"

    def test_token_missing_grant_type_returns_422(
        self,
        test_client: TestClient,
        registered_client: Dict,
    ):
        """Test token request without grant_type."""
        response = test_client.post(
            self.TOKEN_URL,
            data={
                "client_id": registered_client["client_id"],
                "client_secret": registered_client["client_secret"],
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_token_invalid_grant_type_returns_422(
        self,
        test_client: TestClient,
        registered_client: Dict,
    ):
        """Test token request with unsupported grant_type."""
        response = test_client.post(
            self.TOKEN_URL,
            data={
                "grant_type": "password",
                "client_id": registered_client["client_id"],
                "client_secret": registered_client["client_secret"],
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_token_invalid_scope_returns_400(
        self,
        test_client: TestClient,
        registered_client: Dict,
    ):
        """Test token request with unauthorized scope."""
        response = test_client.post(
            self.TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": registered_client["client_id"],
                "client_secret": registered_client["client_secret"],
                "scope": "admin:full",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        data = response.json()
        assert data["detail"]["error"] == "invalid_scope"

    def test_token_invalid_client_id_format_returns_422(
        self,
        test_client: TestClient,
        registered_client: Dict,
    ):
        """Test token request with invalid client_id format."""
        from tests.conftest import generate_invalid_client_id
        
        response = test_client.post(
            self.TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": generate_invalid_client_id(),
                "client_secret": registered_client["client_secret"],
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_token_invalid_client_secret_format_returns_422(
        self,
        test_client: TestClient,
        registered_client: Dict,
    ):
        """Test token request with invalid client_secret format."""
        from tests.conftest import generate_invalid_client_secret
        
        response = test_client.post(
            self.TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": registered_client["client_id"],
                "client_secret": generate_invalid_client_secret(),
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_token_expires_in_is_positive(
        self,
        test_client: TestClient,
        registered_client: Dict,
    ):
        """Test that expires_in is a positive integer."""
        response = test_client.post(
            self.TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": registered_client["client_id"],
                "client_secret": registered_client["client_secret"],
            },
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert isinstance(data["expires_in"], int)
        assert data["expires_in"] > 0

    def test_token_type_is_bearer(
        self,
        test_client: TestClient,
        registered_client: Dict,
    ):
        """Test that token_type is always 'Bearer'."""
        response = test_client.post(
            self.TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": registered_client["client_id"],
                "client_secret": registered_client["client_secret"],
            },
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["token_type"] == "Bearer"

    def test_token_multiple_requests_return_different_tokens(
        self,
        test_client: TestClient,
        registered_client: Dict,
    ):
        """Test that multiple token requests return different tokens."""
        response1 = test_client.post(
            self.TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": registered_client["client_id"],
                "client_secret": registered_client["client_secret"],
            },
        )
        response2 = test_client.post(
            self.TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": registered_client["client_id"],
                "client_secret": registered_client["client_secret"],
            },
        )

        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK

        token1 = response1.json()["access_token"]
        token2 = response2.json()["access_token"]

        # Tokens should be different (different jti)
        assert token1 != token2

    def test_token_default_scope_when_not_specified(
        self,
        test_client: TestClient,
        registered_client: Dict,
    ):
        """Test that default scope is used when not specified."""
        response = test_client.post(
            self.TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": registered_client["client_id"],
                "client_secret": registered_client["client_secret"],
            },
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        # Should contain the client's allowed scopes
        assert "catalog:read" in data["scope"]
