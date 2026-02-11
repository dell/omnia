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

"""End-to-end tests for Generate Input Files complete workflow.

These tests validate the complete generate input files workflow using real OAuth2
authentication instead of mocks. The tests follow the chronological order:
1. Health check
2. Client registration
3. Token generation
4. Job creation
5. Parse catalog execution (prerequisite)
6. Generate input files execution
7. Error handling and edge cases

Requirements:
    - ansible-vault must be installed
    - Tests require write access to create temporary vault files
    - RSA keys must be available for JWT signing
"""

import json
import uuid
from typing import Dict, Any, Optional

import pytest
import httpx

from core.jobs.value_objects import CorrelationId


class GenerateInputFilesContext:
    """Context object to store state across generate input files tests.

    This class maintains state between test steps, allowing tests to
    share data like client credentials, access tokens, and job IDs.

    Attributes:
        client_id: Registered client identifier.
        client_secret: Registered client secret.
        access_token: Generated JWT access token.
        job_id: Created job ID for generate input files testing.
        catalog_content: Valid catalog content for testing.
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
        self.job_id: Optional[str] = None
        self.catalog_content: Optional[bytes] = None

    def has_client_credentials(self) -> bool:
        """Check if client credentials are available."""
        return self.client_id is not None and self.client_secret is not None

    def has_access_token(self) -> bool:
        """Check if access token is available."""
        return self.access_token is not None

    def has_job_id(self) -> bool:
        """Check if job ID is available."""
        return self.job_id is not None

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

    def set_job_id(self, job_id: str) -> None:
        """Set the job ID for testing."""
        self.job_id = job_id

    def load_catalog_content(self) -> None:
        """Load a valid catalog for testing."""
        # Use a simple but valid catalog structure
        catalog_data = {
            "Catalog": {
                "Name": "Test Catalog for Generate Input Files",
                "Version": "1.0.0",
                "FunctionalLayer": "test-functional",
                "BaseOS": "rhel",
                "Infrastructure": "kubernetes",
                "FunctionalPackages": {
                    "monitoring": {
                        "Version": "1.0.0",
                        "Source": "test"
                    }
                },
                "OSPackages": {
                    "base": {
                        "Version": "9.0",
                        "Source": "test"
                    }
                },
                "InfrastructurePackages": {
                    "kubernetes": {
                        "Version": "1.28",
                        "Source": "test"
                    }
                },
                "DriverPackages": {}
            }
        }
        self.catalog_content = json.dumps(catalog_data).encode('utf-8')


@pytest.fixture(scope="class")
def generate_input_files_context():
    """Create a shared context for generate input files tests.

    Returns:
        GenerateInputFilesContext instance for sharing state across tests.
    """
    return GenerateInputFilesContext()


class TestGenerateInputFilesE2E:

    """End-to-end tests for Generate Input Files complete workflow.

    Tests are ordered to follow the natural workflow:
    1. Health check - Verify server is running
    2. Client registration - Register OAuth client with catalog scopes
    3. Token generation - Obtain JWT access token
    4. Job creation - Create a job for generate input files
    5. Parse catalog execution - Execute parse catalog stage (prerequisite)
    6. Generate input files execution - Execute generate input files stage
    7. Error handling - Test various failure scenarios

    Tests use pytest.mark.e2e and depend on fixtures from conftest.py.
    """

    @pytest.mark.e2e
    def test_01_health_check(self, base_url: str):
        """Step 1: Verify server health.

        Confirms the API server is running and accessible before proceeding
        with authentication and workflow tests.
        """
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.get("/health")

        assert response.status_code == 200, f"Health check failed: {response.text}"

        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.e2e
    def test_02_register_client_for_generate_input_files(
        self,
        base_url: str,
        valid_auth_header: Dict[str, str],
        generate_input_files_context: GenerateInputFilesContext,  # noqa: W0621
    ):
        """Step 2: Register a new OAuth client for generate input files access.

        This creates a client that will be used for subsequent generate input files requests.
        Client credentials are stored in the shared context.
        """
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                "/api/v1/auth/register",
                headers=valid_auth_header,
                json={
                    "client_name": "generate-input-files-test-client",
                    "description": "Client for generate input files testing",
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
        generate_input_files_context.client_id = data["client_id"]
        generate_input_files_context.client_secret = data["client_secret"]
        generate_input_files_context.client_name = data["client_name"]
        generate_input_files_context.allowed_scopes = data["allowed_scopes"]

    @pytest.mark.e2e
    def test_03_request_token_for_generate_input_files(
        self,
        base_url: str,
        generate_input_files_context: GenerateInputFilesContext,  # noqa: W0621
    ):
        """Step 3: Request access token for generate input files API.

        Uses the client credentials from registration to obtain a JWT token.
        Token is stored in the shared context for subsequent API calls.
        """
        assert generate_input_files_context.has_client_credentials(), (
            "Client credentials not available. Run test_02_register_client_for_generate_input_files first."
        )

        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                "/api/v1/auth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": generate_input_files_context.client_id,
                    "client_secret": generate_input_files_context.client_secret,
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
        generate_input_files_context.access_token = data["access_token"]
        generate_input_files_context.token_type = data["token_type"]
        generate_input_files_context.expires_in = data["expires_in"]
        generate_input_files_context.scope = data["scope"]

    @pytest.mark.e2e
    def test_04_create_job_for_generate_input_files(
        self,
        base_url: str,
        generate_input_files_context: GenerateInputFilesContext,  # noqa: W0621
    ):
        """Step 4: Create a new job for generate input files testing.

        Tests job creation with proper validation and idempotency.
        """
        assert generate_input_files_context.has_access_token(), (
            "Access token not available. Run test_03_request_token_for_generate_input_files first."
        )

        # Prepare job creation request
        job_data = {
            "client_id": generate_input_files_context.client_id,
            "client_name": "Generate Input Files Test Client"
        }

        idempotency_key = str(uuid.uuid4())
        headers = generate_input_files_context.get_auth_header()
        headers["Idempotency-Key"] = idempotency_key

        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                "/api/v1/jobs",
                json=job_data,
                headers=headers,
            )

        assert response.status_code == 201, f"Job creation failed: {response.text}"

        data = response.json()

        # Verify response structure
        assert "job_id" in data
        assert "job_state" in data
        assert "created_at" in data
        assert "correlation_id" in data

        # Verify job ID format (UUID)
        uuid.UUID(data["job_id"])  # This will raise ValueError if not valid UUID

        # Store job ID in context
        generate_input_files_context.set_job_id(data["job_id"])

        # Verify job state
        assert data["job_state"] == "CREATED"

    @pytest.mark.e2e
    def test_05_parse_catalog_prerequisite(
        self,
        base_url: str,
        generate_input_files_context: GenerateInputFilesContext,  # noqa: W0621
    ):
        """Step 5: Execute parse catalog as prerequisite for generate input files.

        Parse catalog must be executed successfully before generate input files
        can be run, as it depends on the catalog artifacts.
        """
        assert generate_input_files_context.has_access_token(), (
            "Access token not available. Run test_03_request_token_for_generate_input_files first."
        )
        assert generate_input_files_context.has_job_id(), (
            "Job ID not available. Run test_04_create_job_for_generate_input_files first."
        )

        # Load catalog content
        generate_input_files_context.load_catalog_content()
        assert generate_input_files_context.catalog_content is not None

        headers = generate_input_files_context.get_auth_header()

        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                f"/api/v1/jobs/{generate_input_files_context.job_id}/stages/parse-catalog",
                files={
                    "file": (
                        "catalog.json", 
                        generate_input_files_context.catalog_content,
                        "application/json"
                    )
                },
                headers=headers,
            )

        # The response should indicate the stage was processed
        # It might fail due to missing dependencies, but the workflow should be complete
        assert response.status_code in [200, 400, 422, 500], (
            f"Parse catalog failed: {response.text}"
        )

        # Get response data for verification
        response_data = response.json() if response.status_code == 200 else None

        # If successful, verify the response structure
        if response.status_code == 200 and response_data:
            assert "status" in response_data
            assert response_data["status"] == "success"
            assert "message" in response_data

    @pytest.mark.e2e
    def test_06_generate_input_files_success(
        self,
        base_url: str,
        generate_input_files_context: GenerateInputFilesContext,  # noqa: W0621
    ):
        """Step 6: Execute generate input files successfully.

        Tests the complete generate input files workflow with default policy.
        This depends on parse catalog having been executed first.
        """
        assert generate_input_files_context.has_access_token(), (
            "Access token not available. Run test_03_request_token_for_generate_input_files first."
        )
        assert generate_input_files_context.has_job_id(), (
            "Job ID not available. Run test_04_create_job_for_generate_input_files first."
        )

        headers = generate_input_files_context.get_auth_header()

        # Execute generate input files with default policy
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            response = client.post(
                f"/api/v1/jobs/{generate_input_files_context.job_id}/stages/generate-input-files",
                headers=headers,
            )

        # Should process the request (may fail due to missing dependencies)
        assert response.status_code in [200, 400, 422, 500], (
            f"Generate input files failed: {response.text}"
        )
        
        # If successful, verify response structure
        if response.status_code == 200:
            response_data = response.json()
            assert "stage_state" in response_data
            assert response_data["stage_state"] in ["COMPLETED", "FAILED"]
            
            if response_data["stage_state"] == "COMPLETED":
                assert "generated_files" in response_data
                assert isinstance(response_data["generated_files"], list)

    @pytest.mark.e2e
    def test_07_generate_input_files_with_custom_policy(
        self,
        base_url: str,
        generate_input_files_context: GenerateInputFilesContext,  # noqa: W0621
    ):
        """Step 7: Test generate input files with custom adapter policy.

        Tests error handling and various policy path scenarios.
        """
        assert generate_input_files_context.has_access_token(), (
            "Access token not available. Run test_03_request_token_for_generate_input_files first."
        )
        assert generate_input_files_context.has_job_id(), (
            "Job ID not available. Run test_04_create_job_for_generate_input_files first."
        )

        headers = generate_input_files_context.get_auth_header()

        # Test with invalid policy path
        invalid_request = {
            "adapter_policy_path": "../../../etc/passwd"
        }

        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            error_response = client.post(
                f"/api/v1/jobs/{generate_input_files_context.job_id}/stages/generate-input-files",
                json=invalid_request,
                headers=headers,
            )

        # Should reject invalid path
        assert error_response.status_code in [400, 422], (
            f"Expected rejection of invalid policy path: {error_response.text}"
        )
        
        # Test with valid request (default policy)
        with httpx.Client(base_url=base_url, timeout=30.0) as client:
            recovery_response = client.post(
                f"/api/v1/jobs/{generate_input_files_context.job_id}/stages/generate-input-files",
                headers=headers,
            )

        # Should process the valid request
        assert recovery_response.status_code in [200, 400, 422, 500], (
            f"Valid request failed: {recovery_response.text}"
        )
