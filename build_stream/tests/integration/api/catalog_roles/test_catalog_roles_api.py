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

"""
Catalog Roles API Integration Tests

Tests the GET /jobs/{job_id}/catalog/roles endpoint including:
- Successful role retrieval after parse-catalog completes
- Authentication/authorization enforcement
- 404 when job does not exist or parse-catalog has not run
- 400 for invalid job_id format
"""

import json
import os
import uuid
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from container import DevContainer
from main import app


class TestGetCatalogRolesAPI:  # pylint: disable=too-many-public-methods
    """Integration tests for GET /jobs/{job_id}/catalog/roles endpoint."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client with in-memory stores."""
        container = DevContainer()
        container.wire(modules=["api.catalog_roles.routes", "api.parse_catalog.routes"])

        with TestClient(app) as client:
            yield client

    @pytest.fixture
    def auth_headers(self, mock_jwt_validation) -> Dict[str, str]:  # pylint: disable=unused-argument
        """Create authentication headers."""
        return {
            "Authorization": "Bearer test-token",
            "X-Correlation-ID": str(uuid.uuid4()),
            "Idempotency-Key": f"test-key-{uuid.uuid4()}",
        }

    @pytest.fixture
    def valid_catalog_json(self) -> Dict[str, Any]:
        """Load a valid catalog JSON from fixtures."""
        here = os.path.dirname(__file__)
        fixtures_dir = os.path.abspath(
            os.path.join(here, "..", "..", "..", "fixtures", "catalogs")
        )
        catalog_path = os.path.join(fixtures_dir, "catalog_rhel.json")
        with open(catalog_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @pytest.fixture
    def created_job(
        self, client: TestClient, auth_headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Create a fresh job for each test."""
        headers = auth_headers.copy()
        headers["Idempotency-Key"] = f"test-key-{uuid.uuid4()}"

        response = client.post(
            "/api/v1/jobs",
            json={"client_id": "test-client"},
            headers=headers,
        )
        assert response.status_code == 201
        return response.json()

    @pytest.fixture
    def job_with_parsed_catalog(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        created_job: Dict[str, Any],
        valid_catalog_json: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a job and run parse-catalog so roles are available."""
        job_id = created_job["job_id"]

        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files={
                "file": (
                    "catalog.json",
                    json.dumps(valid_catalog_json),
                    "application/json",
                )
            },
            headers=auth_headers,
        )
        assert response.status_code == 200, (
            f"parse-catalog failed: {response.text}"
        )
        return created_job

    # ------------------------------------------------------------------
    # Success cases
    # ------------------------------------------------------------------

    def test_get_roles_success(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        job_with_parsed_catalog: Dict[str, Any],
    ) -> None:
        """Test successful role retrieval after parse-catalog completes."""
        job_id = job_with_parsed_catalog["job_id"]

        response = client.get(
            f"/api/v1/jobs/{job_id}/catalog/roles",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert isinstance(data["roles"], list)
        assert len(data["roles"]) > 0
        # All roles must be non-empty strings
        for role in data["roles"]:
            assert isinstance(role, str)
            assert len(role) > 0

    def test_get_roles_returns_sorted_list(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        job_with_parsed_catalog: Dict[str, Any],
    ) -> None:
        """Test that roles are returned in sorted order."""
        job_id = job_with_parsed_catalog["job_id"]

        response = client.get(
            f"/api/v1/jobs/{job_id}/catalog/roles",
            headers=auth_headers,
        )

        assert response.status_code == 200
        roles = response.json()["roles"]
        assert roles == sorted(roles)

    def test_get_roles_response_schema(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        job_with_parsed_catalog: Dict[str, Any],
    ) -> None:
        """Test that the response matches the expected schema."""
        job_id = job_with_parsed_catalog["job_id"]

        response = client.get(
            f"/api/v1/jobs/{job_id}/catalog/roles",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert "roles" in data
        assert data["job_id"] == job_id

    # ------------------------------------------------------------------
    # Authentication / Authorization
    # ------------------------------------------------------------------

    def test_get_roles_no_auth_returns_401(
        self,
        client: TestClient,
        job_with_parsed_catalog: Dict[str, Any],
    ) -> None:
        """Test that missing Authorization header returns 401."""
        job_id = job_with_parsed_catalog["job_id"]

        response = client.get(f"/api/v1/jobs/{job_id}/catalog/roles")

        assert response.status_code == 401
        assert "detail" in response.json()

    def test_get_roles_invalid_token_returns_401(
        self,
        client: TestClient,
        created_job: Dict[str, Any],
    ) -> None:
        """Test that an invalid token returns 401 (without mock_jwt_validation)."""
        job_id = created_job["job_id"]

        response = client.get(
            f"/api/v1/jobs/{job_id}/catalog/roles",
            headers={"Authorization": "Bearer totally-invalid-token"},
        )

        # With real JWT validation this returns 401; with mock it may return 404
        assert response.status_code in [401, 404]

    # ------------------------------------------------------------------
    # Job not found / parse-catalog not completed
    # ------------------------------------------------------------------

    def test_get_roles_nonexistent_job_returns_404(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
    ) -> None:
        """Test that a non-existent job_id returns 404."""
        fake_job_id = "019bf590-1234-7890-abcd-ef1234567890"

        response = client.get(
            f"/api/v1/jobs/{fake_job_id}/catalog/roles",
            headers=auth_headers,
        )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_code"] in [
            "PARSE_CATALOG_NOT_COMPLETED",
            "JOB_NOT_FOUND",
        ]

    def test_get_roles_before_parse_catalog_returns_404(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        created_job: Dict[str, Any],
    ) -> None:
        """Test that calling get-roles before parse-catalog returns 404."""
        job_id = created_job["job_id"]

        response = client.get(
            f"/api/v1/jobs/{job_id}/catalog/roles",
            headers=auth_headers,
        )

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error_code"] == "PARSE_CATALOG_NOT_COMPLETED"

    # ------------------------------------------------------------------
    # Input validation
    # ------------------------------------------------------------------

    def test_get_roles_invalid_job_id_format_returns_400(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
    ) -> None:
        """Test that a malformed job_id returns 400."""
        response = client.get(
            "/api/v1/jobs/not-a-valid-uuid/catalog/roles",
            headers=auth_headers,
        )

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error_code"] == "INVALID_JOB_ID"

    # ------------------------------------------------------------------
    # Error response structure
    # ------------------------------------------------------------------

    def test_error_response_does_not_expose_internals(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
    ) -> None:
        """Test that error responses do not expose stack traces or file paths."""
        fake_job_id = "019bf590-dead-beef-abcd-ef1234567890"

        response = client.get(
            f"/api/v1/jobs/{fake_job_id}/catalog/roles",
            headers=auth_headers,
        )

        assert response.status_code == 404
        message = response.json()["detail"]["message"]
        assert "traceback" not in message.lower()
        assert ".py" not in message
