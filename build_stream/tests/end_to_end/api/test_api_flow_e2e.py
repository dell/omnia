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

"""End-to-end integration tests for complete API workflow.

These tests validate the complete OAuth2 authentication workflow from client registration
through token generation and validation. This test suite focuses on authentication
and authorization mechanisms, providing comprehensive coverage of the auth API.

Usage:
    pytest tests/integration/test_api_flow_e2e.py -v -m e2e

Requirements:
    - ansible-vault must be installed
    - Tests require write access to create temporary vault files
    - RSA keys must be available for JWT signing

Test Flow:
    1. Health check - Verify server is running
    2. Client Registration - Register a new OAuth client with proper scopes
    3. Token Generation - Obtain access token using client credentials
    4. Token Validation - Verify JWT structure, uniqueness, and scope enforcement
    5. Error Handling - Test various failure scenarios and security validations
    6. Security Validation - Verify proper security measures are enforced

Test Classes:
    - TestCompleteAPIFlow: Main workflow tests (happy path scenarios)
    - TestAPIFlowErrorHandling: Error scenario testing
    - TestAPIFlowSecurityValidation: Security measure validation

Key Features Tested:
    - OAuth2 client registration with Basic Auth
    - JWT token generation with client_credentials grant
    - Scope-based authorization (catalog:read, catalog:write)
    - Token uniqueness and validation
    - Error handling and security measures
    - Client credential format validation
    - Maximum client limits enforcement

Note: This test suite focuses specifically on authentication and authorization.
Protected API endpoints (like parse_catalog) are tested separately when implemented.
"""

# pylint: disable=redefined-outer-name

from typing import Dict, Optional

import httpx
import pytest

# Import helper functions from conftest
from tests.end_to_end.api.conftest import (
    generate_test_client_secret,
    generate_invalid_client_id,
    generate_invalid_client_secret,
)


class APIFlowContext:  # noqa: R0902 pylint: disable=too-many-instance-attributes
    """Context object to store state across API flow tests.

    This class maintains state between test steps, allowing tests to
    share data like client credentials and access tokens.

    Attributes:
        client_id: Registered client identifier.
        client_secret: Registered client secret.
        access_token: Generated JWT access token.
        token_type: Token type (Bearer).
        expires_in: Token expiration time in seconds.
        scope: Granted scopes.
    """

    def __init__(self):
        """Initialize empty context."""
        self.client_id: Optional[str] = None
        self.client_secret: Optional[str] = None
        self.client_name: Optional[str] = None
        self.allowed_scopes: Optional[list] = None
        self.access_token: Optional[str] = None
        self.token_type: Optional[str] = None
        self.expires_in: Optional[int] = None
        self.scope: Optional[str] = None

    def has_client_credentials(self) -> bool:
        """Check if client credentials are available."""
        return self.client_id is not None and self.client_secret is not None

    def has_access_token(self) -> bool:
        """Check if access token is available."""
        return self.access_token is not None

    def get_auth_header(self) -> Dict[str, str]:
        """Get Authorization header with Bearer token.

        Returns:
            Dictionary with Authorization header.

        Raises:
            ValueError: If access token is not available.
        """
        if not self.has_access_token():
            raise ValueError("Access token not available")
        return {"Authorization": f"Bearer {self.access_token}"}


@pytest.fixture(scope="class")
def api_flow_context():
    """Create a shared context for API flow tests.

    Returns:
        APIFlowContext instance shared across test class.
    """
    return APIFlowContext()


@pytest.mark.e2e
@pytest.mark.integration
class TestCompleteAPIFlow:
    """End-to-end test suite for complete OAuth2 authentication workflow.

    Tests are ordered to follow the natural authentication flow:
    1. Health check - Verify server is running
    2. Client registration - Register OAuth client with scopes
    3. Token generation - Obtain JWT access token
    4. Token validation - Verify token structure and scopes
    5. Scope enforcement - Test subset and unauthorized scope requests
    6. Security validation - Test invalid credentials and token uniqueness

    Each test builds on the previous, storing state in the shared context.
    This covers the complete authentication and authorization workflow.

    Note: Protected API endpoints are not tested here - they are implemented
    separately when the actual endpoints are available.
    """

    def test_01_health_check(
        self,
        base_url: str,
        reset_vault,  # noqa: W0613 pylint: disable=unused-argument
    ):
        """Step 1: Verify server health endpoint is accessible.

        This confirms the server is running and ready to accept requests.
        """
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.get("/health")

        assert response.status_code == 200, f"Health check failed: {response.text}"

        data = response.json()
        assert data["status"] == "healthy"

    def test_02_register_client(
        self,
        base_url: str,
        valid_auth_header: Dict[str, str],
        api_flow_context: APIFlowContext,  # noqa: W0621
    ):
        """Step 2: Register a new OAuth client.

        This creates a client that will be used for subsequent token requests.
        Client credentials are stored in the shared context.
        """
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                "/api/v1/auth/register",
                headers=valid_auth_header,
                json={
                    "client_name": "api-flow-test-client",
                    "description": "Client for complete API flow testing",
                    "allowed_scopes": ["catalog:read", "catalog:write"],
                },
            )

        assert response.status_code == 201, f"Registration failed: {response.text}"

        data = response.json()

        # Verify response structure
        assert "client_id" in data
        assert "client_secret" in data
        assert data["client_id"].startswith("bld_")
        assert data["client_secret"].startswith("bld_s_")

        # Store credentials in context for subsequent tests
        api_flow_context.client_id = data["client_id"]
        api_flow_context.client_secret = data["client_secret"]
        api_flow_context.client_name = data["client_name"]
        api_flow_context.allowed_scopes = data["allowed_scopes"]

    def test_03_request_token(
        self,
        base_url: str,
        api_flow_context: APIFlowContext,  # noqa: W0621
    ):
        """Step 3: Request access token using client credentials.

        Uses the client credentials from registration to obtain a JWT token.
        Token is stored in the shared context for subsequent API calls.
        """
        assert api_flow_context.has_client_credentials(), (
            "Client credentials not available. Run test_02_register_client first."
        )

        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                "/api/v1/auth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": api_flow_context.client_id,
                    "client_secret": api_flow_context.client_secret,
                },
            )

        assert response.status_code == 200, f"Token request failed: {response.text}"

        data = response.json()

        # Verify response structure
        assert "access_token" in data
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] > 0
        assert "scope" in data

        # Verify JWT structure
        parts = data["access_token"].split(".")
        assert len(parts) == 3, "Token should be valid JWT format"

        # Store token in context for subsequent tests
        api_flow_context.access_token = data["access_token"]
        api_flow_context.token_type = data["token_type"]
        api_flow_context.expires_in = data["expires_in"]
        api_flow_context.scope = data["scope"]

    def test_04_token_contains_granted_scopes(
        self,
        api_flow_context: APIFlowContext,  # noqa: W0621
    ):
        """Step 4: Verify token contains the expected scopes.

        Confirms that the granted scopes match the client's allowed scopes.
        """
        assert api_flow_context.has_access_token(), (
            "Access token not available. Run test_03_request_token first."
        )

        # Verify scopes match what was registered
        granted_scopes = api_flow_context.scope.split()
        for scope in api_flow_context.allowed_scopes:
            assert scope in granted_scopes, f"Expected scope '{scope}' not in token"

    def test_05_request_token_with_subset_scope(
        self,
        base_url: str,
        api_flow_context: APIFlowContext,  # noqa: W0621
    ):
        """Step 5: Request token with a subset of allowed scopes.

        Verifies that clients can request fewer scopes than allowed.
        """
        assert api_flow_context.has_client_credentials(), (
            "Client credentials not available. Run test_02_register_client first."
        )

        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                "/api/v1/auth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": api_flow_context.client_id,
                    "client_secret": api_flow_context.client_secret,
                    "scope": "catalog:read",
                },
            )

        assert response.status_code == 200, f"Token request failed: {response.text}"

        data = response.json()
        assert data["scope"] == "catalog:read"

    def test_06_reject_unauthorized_scope(
        self,
        base_url: str,
        api_flow_context: APIFlowContext,  # noqa: W0621
    ):
        """Step 6: Verify unauthorized scope is rejected.

        Confirms that clients cannot request scopes beyond their allowed set.
        """
        assert api_flow_context.has_client_credentials(), (
            "Client credentials not available. Run test_02_register_client first."
        )

        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                "/api/v1/auth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": api_flow_context.client_id,
                    "client_secret": api_flow_context.client_secret,
                    "scope": "admin:full",
                },
            )

        assert response.status_code == 400, f"Expected 400, got: {response.text}"

        data = response.json()
        assert data["detail"]["error"] == "invalid_scope"

    def test_07_reject_invalid_credentials(
        self,
        base_url: str,
        api_flow_context: APIFlowContext,  # noqa: W0621
    ):
        """Step 7: Verify invalid credentials are rejected.

        Confirms that token requests with wrong credentials fail properly.
        """
        
        assert api_flow_context.has_client_credentials(), (
            "Client credentials not available. Run test_02_register_client first."
        )

        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                "/api/v1/auth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": api_flow_context.client_id,
                    "client_secret": generate_test_client_secret(),
                },
            )

        assert response.status_code == 401, f"Expected 401, got: {response.text}"

        data = response.json()
        assert data["detail"]["error"] == "invalid_client"

    def test_08_multiple_tokens_are_unique(
        self,
        base_url: str,
        api_flow_context: APIFlowContext,  # noqa: W0621
    ):
        """Step 8: Verify each token request generates a unique token.

        Confirms that tokens have unique identifiers (jti claim).
        """
        assert api_flow_context.has_client_credentials(), (
            "Client credentials not available. Run test_02_register_client first."
        )

        tokens = []
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            for _ in range(3):
                response = client.post(
                    "/api/v1/auth/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": api_flow_context.client_id,
                        "client_secret": api_flow_context.client_secret,
                    },
                )
                assert response.status_code == 200
                tokens.append(response.json()["access_token"])

        # All tokens should be unique
        assert len(set(tokens)) == 3, "All tokens should be unique"


@pytest.mark.e2e
@pytest.mark.integration
class TestAPIFlowErrorHandling:
    """Test error handling across the OAuth2 authentication flow.

    These tests verify proper error responses for various failure scenarios:
    - Registration without/with invalid authentication
    - Token requests for unregistered clients
    - Invalid grant types and credentials
    - Format validation for client credentials

    Each test ensures that error responses are appropriate and secure,
    without exposing sensitive information.
    """

    def test_register_without_auth_fails(
        self,
        base_url: str,
        reset_vault,  # noqa: W0613 pylint: disable=unused-argument
    ):
        """Verify registration without authentication fails."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                "/api/v1/auth/register",
                json={"client_name": "unauthorized-client"},
            )

        assert response.status_code == 401, f"Expected 401, got: {response.text}"

    def test_register_with_invalid_auth_fails(
        self,
        base_url: str,
        invalid_auth_header: Dict[str, str],
        reset_vault,  # noqa: W0613 pylint: disable=unused-argument
    ):
        """Verify registration with invalid credentials fails."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                "/api/v1/auth/register",
                headers=invalid_auth_header,
                json={"client_name": "invalid-auth-client"},
            )

        assert response.status_code == 401, f"Expected 401, got: {response.text}"

    def test_token_without_registration_fails(
        self,
        base_url: str,
        reset_vault,  # noqa: W0613 pylint: disable=unused-argument
    ):
        """Verify token request for unregistered client fails."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                "/api/v1/auth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": "bld_nonexistent_client_12345678",
                    "client_secret": generate_test_client_secret(),
                },
            )

        assert response.status_code == 401, f"Expected 401, got: {response.text}"

        data = response.json()
        assert data["detail"]["error"] == "invalid_client"

    def test_token_with_invalid_grant_type_fails(
        self,
        base_url: str,
        valid_auth_header: Dict[str, str],
        reset_vault,  # noqa: W0613 pylint: disable=unused-argument
    ):
        """Verify token request with unsupported grant type fails."""
        # First register a client
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            reg_response = client.post(
                "/api/v1/auth/register",
                headers=valid_auth_header,
                json={"client_name": "grant-type-test-client"},
            )
            assert reg_response.status_code == 201

            creds = reg_response.json()

            # Try token with invalid grant type
            response = client.post(
                "/api/v1/auth/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": creds["client_id"],
                    "client_secret": creds["client_secret"],
                },
            )

        assert response.status_code == 422, f"Expected 422, got: {response.text}"


@pytest.mark.e2e
@pytest.mark.integration
class TestAPIFlowSecurityValidation:
    """Security validation tests for the OAuth2 authentication flow.

    These tests verify that security measures are properly enforced:
    - Client credential format validation
    - Maximum client limits enforcement
    - Proper error handling without information disclosure
    - Token security and uniqueness validation

    These tests ensure the authentication system follows security best practices
    and does not expose sensitive information in error responses.
    """

    def test_client_credentials_format_validation(
        self,
        base_url: str,
        reset_vault,  # noqa: W0613 pylint: disable=unused-argument
    ):
        """Verify client credential format validation."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            # Invalid client_id format
            response = client.post(
                "/api/v1/auth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": generate_invalid_client_id(),
                    "client_secret": generate_test_client_secret(),
                },
            )

        assert response.status_code == 422, f"Expected 422, got: {response.text}"

    def test_client_secret_format_validation(
        self,
        base_url: str,
        reset_vault,  # noqa: W0613 pylint: disable=unused-argument
    ):
        """Verify client secret format validation."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                "/api/v1/auth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": "bld_valid_format_client_id",
                    "client_secret": generate_invalid_client_secret(),
                },
            )

        assert response.status_code == 422, f"Expected 422, got: {response.text}"

    def test_max_clients_limit_enforced(
        self,
        base_url: str,
        valid_auth_header: Dict[str, str],
        reset_vault,  # noqa: W0613 pylint: disable=unused-argument
    ):
        """Verify maximum client limit is enforced."""
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            # Register first client
            response1 = client.post(
                "/api/v1/auth/register",
                headers=valid_auth_header,
                json={"client_name": "first-client"},
            )
            assert response1.status_code == 201

            # Try to register second client
            response2 = client.post(
                "/api/v1/auth/register",
                headers=valid_auth_header,
                json={"client_name": "second-client"},
            )

        assert response2.status_code == 409, f"Expected 409, got: {response2.text}"

        data = response2.json()
        assert data["detail"]["error"] == "max_clients_reached"
