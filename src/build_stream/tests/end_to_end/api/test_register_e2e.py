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

"""End-to-end integration tests for the /api/v1/auth/register endpoint.

These tests run against a real FastAPI server with actual Ansible Vault,
providing true end-to-end validation of the registration flow.

Usage:
    pytest tests/integration/test_register_e2e.py -v -m e2e

Requirements:
    - ansible-vault must be installed
    - Tests require write access to create temporary vault files
"""

from typing import Dict

import httpx
import pytest


@pytest.mark.e2e
@pytest.mark.integration
class TestRegisterEndpointE2E:
    """End-to-end test suite for POST /api/v1/auth/register endpoint.

    These tests validate the complete registration flow with real Ansible Vault.
    """

    REGISTER_URL = "/api/v1/auth/register"

    def test_register_valid_credentials_returns_201(
        self,
        base_url: str,
        valid_auth_header: Dict[str, str],
        reset_vault,  # noqa: W0613
    ):
        """Test successful client registration with valid credentials.

        Verifies the complete registration flow:
        1. Basic Auth verification against real encrypted vault
        2. Client credential generation (Argon2id hashing)
        3. Vault encryption and storage of client credentials
        4. Response with client_id and client_secret
        """
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.REGISTER_URL,
                headers=valid_auth_header,
                json={
                    "client_name": "test-client-e2e",
                    "description": "End-to-end test client",
                    "allowed_scopes": ["catalog:read", "catalog:write"],
                },
            )

        assert response.status_code == 201, f"Response: {response.text}"

        data = response.json()
        assert "client_id" in data
        assert "client_secret" in data
        assert data["client_id"].startswith("bld_")
        assert data["client_secret"].startswith("bld_s_")
        assert data["client_name"] == "test-client-e2e"
        assert data["allowed_scopes"] == ["catalog:read", "catalog:write"]
        assert "created_at" in data

    def test_register_minimal_request_returns_201(
        self,
        base_url: str,
        valid_auth_header: Dict[str, str],
        reset_vault,  # noqa: W0613
    ):
        """Test registration with only required fields uses default scopes."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.REGISTER_URL,
                headers=valid_auth_header,
                json={"client_name": "minimal-client"},
            )

        assert response.status_code == 201, f"Response: {response.text}"

        data = response.json()
        assert data["client_name"] == "minimal-client"
        assert data["allowed_scopes"] == ["catalog:read"]

    def test_register_max_clients_reached_returns_409(
        self,
        base_url: str,
        valid_auth_header: Dict[str, str],
        reset_vault,  # noqa: W0613
    ):
        """Test registration fails when max clients (1) already registered.

        Verifies the single-client limit enforcement:
        1. First registration succeeds
        2. Second registration fails with 409 Conflict
        """
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response1 = client.post(
                self.REGISTER_URL,
                headers=valid_auth_header,
                json={"client_name": "first-client"},
            )
            assert response1.status_code == 201, f"First registration failed: {response1.text}"

            response2 = client.post(
                self.REGISTER_URL,
                headers=valid_auth_header,
                json={"client_name": "second-client"},
            )

        assert response2.status_code == 409, f"Response: {response2.text}"

        data = response2.json()
        assert data["detail"]["error"] == "max_clients_reached"

    def test_register_invalid_auth_returns_401(
        self,
        base_url: str,
        invalid_auth_header: Dict[str, str],
        reset_vault,  # noqa: W0613
    ):
        """Test registration with invalid Basic Auth credentials fails."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.REGISTER_URL,
                headers=invalid_auth_header,
                json={"client_name": "test-client"},
            )

        assert response.status_code == 401, f"Response: {response.text}"

        data = response.json()
        assert data["detail"]["error"] == "invalid_credentials"

    def test_register_missing_auth_returns_401(
        self,
        base_url: str,
        reset_vault,  # noqa: W0613
    ):
        """Test registration without Authorization header fails."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.REGISTER_URL,
                json={"client_name": "test-client"},
            )

        assert response.status_code == 401, f"Response: {response.text}"

    def test_register_invalid_client_name_returns_422(
        self,
        base_url: str,
        valid_auth_header: Dict[str, str],
        reset_vault,  # noqa: W0613
    ):
        """Test registration with invalid client_name format fails validation."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.REGISTER_URL,
                headers=valid_auth_header,
                json={"client_name": "invalid name with spaces!"},
            )

        assert response.status_code == 422, f"Response: {response.text}"

    def test_register_empty_client_name_returns_422(
        self,
        base_url: str,
        valid_auth_header: Dict[str, str],
        reset_vault,  # noqa: W0613
    ):
        """Test registration with empty client_name fails validation."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.REGISTER_URL,
                headers=valid_auth_header,
                json={"client_name": ""},
            )

        assert response.status_code == 422, f"Response: {response.text}"

    def test_register_missing_client_name_returns_422(
        self,
        base_url: str,
        valid_auth_header: Dict[str, str],
        reset_vault,  # noqa: W0613
    ):
        """Test registration without client_name field fails validation."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.REGISTER_URL,
                headers=valid_auth_header,
                json={"description": "Missing client_name"},
            )

        assert response.status_code == 422, f"Response: {response.text}"

    def test_register_invalid_scope_returns_422(
        self,
        base_url: str,
        valid_auth_header: Dict[str, str],
        reset_vault,  # noqa: W0613
    ):
        """Test registration with invalid scope value fails validation."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.REGISTER_URL,
                headers=valid_auth_header,
                json={
                    "client_name": "test-client",
                    "allowed_scopes": ["invalid_scope"],
                },
            )

        assert response.status_code == 422, f"Response: {response.text}"

    def test_register_client_name_too_long_returns_422(
        self,
        base_url: str,
        valid_auth_header: Dict[str, str],
        reset_vault,  # noqa: W0613
    ):
        """Test registration with client_name exceeding max length fails."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.REGISTER_URL,
                headers=valid_auth_header,
                json={"client_name": "a" * 65},
            )

        assert response.status_code == 422, f"Response: {response.text}"

    def test_register_response_contains_all_fields(
        self,
        base_url: str,
        valid_auth_header: Dict[str, str],
        reset_vault,  # noqa: W0613
    ):
        """Test that successful response contains all expected fields."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.REGISTER_URL,
                headers=valid_auth_header,
                json={
                    "client_name": "complete-client",
                    "description": "Test all fields",
                    "allowed_scopes": ["catalog:read"],
                },
            )

        assert response.status_code == 201, f"Response: {response.text}"

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
        base_url: str,
        valid_auth_header: Dict[str, str],
        reset_vault,  # noqa: W0613
    ):
        """Test that client_id follows expected format: bld_<32_hex>."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.REGISTER_URL,
                headers=valid_auth_header,
                json={"client_name": "format-test-client"},
            )

        assert response.status_code == 201, f"Response: {response.text}"

        data = response.json()
        client_id = data["client_id"]

        assert client_id.startswith("bld_")
        assert len(client_id) == 36  # bld_ (4) + 32 hex chars

        hex_part = client_id[4:]
        assert all(c in "0123456789abcdef" for c in hex_part)

    def test_register_client_secret_format(
        self,
        base_url: str,
        valid_auth_header: Dict[str, str],
        reset_vault,  # noqa: W0613
    ):
        """Test that client_secret follows expected format: bld_s_<base64>."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.REGISTER_URL,
                headers=valid_auth_header,
                json={"client_name": "secret-format-client"},
            )

        assert response.status_code == 201, f"Response: {response.text}"

        data = response.json()
        client_secret = data["client_secret"]

        assert client_secret.startswith("bld_s_")
        assert len(client_secret) > 40  # Prefix + base64 encoded bytes

    def test_register_malformed_json_returns_422(
        self,
        base_url: str,
        valid_auth_header: Dict[str, str],
        reset_vault,  # noqa: W0613
    ):
        """Test registration with malformed JSON body fails."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.REGISTER_URL,
                headers={**valid_auth_header, "Content-Type": "application/json"},
                content="{invalid json",
            )

        assert response.status_code == 422, f"Response: {response.text}"

    def test_register_wrong_content_type_returns_422(
        self,
        base_url: str,
        valid_auth_header: Dict[str, str],
        reset_vault,  # noqa: W0613
    ):
        """Test registration with wrong content type fails."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.REGISTER_URL,
                headers={**valid_auth_header, "Content-Type": "text/plain"},
                content="client_name=test",
            )

        assert response.status_code == 422, f"Response: {response.text}"

    def test_register_malformed_basic_auth_returns_401(
        self,
        base_url: str,
        reset_vault,  # noqa: W0613
    ):
        """Test registration with malformed Basic Auth header fails."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.REGISTER_URL,
                headers={"Authorization": "Basic not-valid-base64!!!"},
                json={"client_name": "test-client"},
            )

        assert response.status_code == 401, f"Response: {response.text}"

    def test_register_bearer_auth_returns_401(
        self,
        base_url: str,
        reset_vault,  # noqa: W0613
    ):
        """Test registration with Bearer auth instead of Basic fails."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.REGISTER_URL,
                headers={"Authorization": "Bearer some-token"},
                json={"client_name": "test-client"},
            )

        assert response.status_code == 401, f"Response: {response.text}"

    def test_register_special_characters_in_client_name(
        self,
        base_url: str,
        valid_auth_header: Dict[str, str],
        reset_vault,  # noqa: W0613
    ):
        """Test registration with valid special characters in client_name."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.REGISTER_URL,
                headers=valid_auth_header,
                json={"client_name": "my-client_v2"},
            )

        assert response.status_code == 201, f"Response: {response.text}"
        assert response.json()["client_name"] == "my-client_v2"

    def test_register_description_with_unicode(
        self,
        base_url: str,
        valid_auth_header: Dict[str, str],
        reset_vault,  # noqa: W0613
    ):
        """Test registration with unicode characters in description."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.REGISTER_URL,
                headers=valid_auth_header,
                json={
                    "client_name": "unicode-client",
                    "description": "Test client with émojis 🚀 and spëcial chârs",
                },
            )

        assert response.status_code == 201, f"Response: {response.text}"

    def test_register_all_valid_scopes(
        self,
        base_url: str,
        valid_auth_header: Dict[str, str],
        reset_vault,  # noqa: W0613
    ):
        """Test registration with all valid scope combinations."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                self.REGISTER_URL,
                headers=valid_auth_header,
                json={
                    "client_name": "all-scopes-client",
                    "allowed_scopes": ["catalog:read", "catalog:write"],
                },
            )

        assert response.status_code == 201, f"Response: {response.text}"
        data = response.json()
        assert set(data["allowed_scopes"]) == {"catalog:read", "catalog:write"}
