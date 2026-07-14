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

"""Integration tests for the /api/v1/auth/register endpoint."""

from typing import Dict

import pytest
from fastapi import status
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestRegisterEndpoint:
    """Test suite for POST /api/v1/auth/register endpoint."""

    REGISTER_URL = "/api/v1/auth/register"

    def test_register_valid_credentials_returns_201(
        self,
        test_client: TestClient,
        valid_auth_header: Dict[str, str],
        valid_registration_request: Dict,
    ):
        """Test successful client registration with valid credentials."""
        response = test_client.post(
            self.REGISTER_URL,
            headers=valid_auth_header,
            json=valid_registration_request,
        )

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert "client_id" in data
        assert "client_secret" in data
        assert data["client_id"].startswith("bld_")
        assert data["client_secret"].startswith("bld_s_")
        assert data["client_name"] == valid_registration_request["client_name"]
        assert data["allowed_scopes"] == valid_registration_request["allowed_scopes"]
        assert "created_at" in data

    def test_register_minimal_request_returns_201(
        self,
        test_client: TestClient,
        valid_auth_header: Dict[str, str],
        minimal_registration_request: Dict,
    ):
        """Test registration with only required fields."""
        response = test_client.post(
            self.REGISTER_URL,
            headers=valid_auth_header,
            json=minimal_registration_request,
        )

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["client_name"] == minimal_registration_request["client_name"]
        assert data["allowed_scopes"] == ["catalog:read"]

    def test_register_invalid_auth_returns_401(
        self,
        test_client: TestClient,
        invalid_auth_header: Dict[str, str],
        valid_registration_request: Dict,
    ):
        """Test registration with invalid Basic Auth credentials."""
        response = test_client.post(
            self.REGISTER_URL,
            headers=invalid_auth_header,
            json=valid_registration_request,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        data = response.json()
        assert data["detail"]["error"] == "invalid_credentials"

    def test_register_missing_auth_returns_401(
        self,
        test_client: TestClient,
        valid_registration_request: Dict,
    ):
        """Test registration without Authorization header."""
        response = test_client.post(
            self.REGISTER_URL,
            json=valid_registration_request,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_register_max_clients_reached_returns_409(
        self,
        test_client_with_existing_client: TestClient,
        valid_auth_header: Dict[str, str],
        valid_registration_request: Dict,
    ):
        """Test registration when max clients (1) already registered."""
        response = test_client_with_existing_client.post(
            self.REGISTER_URL,
            headers=valid_auth_header,
            json=valid_registration_request,
        )

        assert response.status_code == status.HTTP_409_CONFLICT

        data = response.json()
        assert data["detail"]["error"] == "max_clients_reached"

    def test_register_duplicate_client_name_returns_409(
        self,
        test_client: TestClient,
        valid_auth_header: Dict[str, str],
        valid_registration_request: Dict,
    ):
        """Test registration with duplicate client name."""
        response1 = test_client.post(
            self.REGISTER_URL,
            headers=valid_auth_header,
            json=valid_registration_request,
        )
        assert response1.status_code == status.HTTP_201_CREATED

        response2 = test_client.post(
            self.REGISTER_URL,
            headers=valid_auth_header,
            json=valid_registration_request,
        )

        assert response2.status_code == status.HTTP_409_CONFLICT
        data = response2.json()
        assert data["detail"]["error"] in ["client_exists", "max_clients_reached"]

    def test_register_invalid_client_name_returns_422(
        self,
        test_client: TestClient,
        valid_auth_header: Dict[str, str],
    ):
        """Test registration with invalid client_name format."""
        invalid_request = {
            "client_name": "invalid name with spaces!",
        }

        response = test_client.post(
            self.REGISTER_URL,
            headers=valid_auth_header,
            json=invalid_request,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_register_empty_client_name_returns_422(
        self,
        test_client: TestClient,
        valid_auth_header: Dict[str, str],
    ):
        """Test registration with empty client_name."""
        invalid_request = {
            "client_name": "",
        }

        response = test_client.post(
            self.REGISTER_URL,
            headers=valid_auth_header,
            json=invalid_request,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_register_missing_client_name_returns_422(
        self,
        test_client: TestClient,
        valid_auth_header: Dict[str, str],
    ):
        """Test registration without client_name field."""
        invalid_request = {
            "description": "Missing client_name",
        }

        response = test_client.post(
            self.REGISTER_URL,
            headers=valid_auth_header,
            json=invalid_request,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_register_invalid_scope_returns_422(
        self,
        test_client: TestClient,
        valid_auth_header: Dict[str, str],
    ):
        """Test registration with invalid scope value."""
        invalid_request = {
            "client_name": "test-client",
            "allowed_scopes": ["invalid_scope"],
        }

        response = test_client.post(
            self.REGISTER_URL,
            headers=valid_auth_header,
            json=invalid_request,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_register_client_name_too_long_returns_422(
        self,
        test_client: TestClient,
        valid_auth_header: Dict[str, str],
    ):
        """Test registration with client_name exceeding max length."""
        invalid_request = {
            "client_name": "a" * 65,
        }

        response = test_client.post(
            self.REGISTER_URL,
            headers=valid_auth_header,
            json=invalid_request,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_register_response_contains_all_fields(
        self,
        test_client: TestClient,
        valid_auth_header: Dict[str, str],
        valid_registration_request: Dict,
    ):
        """Test that successful response contains all expected fields."""
        response = test_client.post(
            self.REGISTER_URL,
            headers=valid_auth_header,
            json=valid_registration_request,
        )

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        expected_fields = [
            "client_id",
            "client_secret",
            "client_name",
            "allowed_scopes",
            "created_at",
            "expires_at",
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"

    def test_register_client_id_format(
        self,
        test_client: TestClient,
        valid_auth_header: Dict[str, str],
        minimal_registration_request: Dict,
    ):
        """Test that client_id follows expected format: bld_<32_hex>."""
        response = test_client.post(
            self.REGISTER_URL,
            headers=valid_auth_header,
            json=minimal_registration_request,
        )

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        client_id = data["client_id"]

        assert client_id.startswith("bld_")
        assert len(client_id) == 36  # bld_ (4) + 32 hex chars

        hex_part = client_id[4:]
        assert all(c in "0123456789abcdef" for c in hex_part)

    def test_register_client_secret_format(
        self,
        test_client: TestClient,
        valid_auth_header: Dict[str, str],
        minimal_registration_request: Dict,
    ):
        """Test that client_secret follows expected format: bld_s_<base64>."""
        response = test_client.post(
            self.REGISTER_URL,
            headers=valid_auth_header,
            json=minimal_registration_request,
        )

        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        client_secret = data["client_secret"]

        assert client_secret.startswith("bld_s_")
        assert len(client_secret) > 40  # Prefix + base64 encoded bytes
