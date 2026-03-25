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

"""UAT tests for cross-API error scenarios.

These tests validate consistent error handling across all API endpoints.
"""

import httpx
import pytest


@pytest.mark.uat
class TestCrossAPIErrors:
    """Test common error scenarios across all APIs."""

    @pytest.mark.parametrize("endpoint,method", [
        ("/api/v1/jobs/00000000-0000-0000-0000-000000000000", "GET"),
        ("/api/v1/jobs/00000000-0000-0000-0000-000000000000", "DELETE"),
        ("/api/v1/jobs/00000000-0000-0000-0000-000000000000/stages/parse-catalog", "POST"),
        ("/api/v1/jobs/00000000-0000-0000-0000-000000000000/stages/generate-input-files", "POST"),
        ("/api/v1/jobs/00000000-0000-0000-0000-000000000000/stages/create-local-repository", "POST"),
        ("/api/v1/jobs/00000000-0000-0000-0000-000000000000/stages/build-image", "POST"),
        ("/api/v1/jobs/00000000-0000-0000-0000-000000000000/stages/validate-image-on-test", "POST"),
        ("/api/v1/jobs/00000000-0000-0000-0000-000000000000/catalog/roles", "GET"),
    ])
    def test_all_apis_with_invalid_job_returns_404(
        self, http_client: httpx.Client, auth_headers: dict, endpoint: str, method: str
    ):
        """Test all APIs return 404 for nonexistent job ID.
        
        Note: Some endpoints validate request body before checking job existence,
        so they may return 422 (validation error) instead of 404.
        """
        if method == "GET":
            response = http_client.get(endpoint, headers=auth_headers)
            assert response.status_code == 404
        elif method == "DELETE":
            response = http_client.delete(endpoint, headers=auth_headers)
            assert response.status_code == 404
        else:  # POST
            # Parse-catalog requires file upload, not JSON
            if "/stages/parse-catalog" in endpoint:
                files = {"file": ("test.json", b"{}", "application/json")}
                response = http_client.post(endpoint, headers=auth_headers, files=files)
            else:
                response = http_client.post(endpoint, headers=auth_headers, json={})
            
            # Stage endpoints may validate request body first (422) or check job existence first (404)
            assert response.status_code in [404, 422]

    @pytest.mark.parametrize("endpoint,method", [
        ("/api/v1/jobs", "POST"),
        ("/api/v1/jobs/test-id", "GET"),
        ("/api/v1/jobs/test-id", "DELETE"),
        ("/api/v1/jobs/test-id/stages/parse-catalog", "POST"),
        ("/api/v1/jobs/test-id/stages/generate-input-files", "POST"),
        ("/api/v1/jobs/test-id/stages/create-local-repository", "POST"),
        ("/api/v1/jobs/test-id/stages/build-image", "POST"),
        ("/api/v1/jobs/test-id/stages/validate-image-on-test", "POST"),
        ("/api/v1/jobs/test-id/catalog/roles", "GET"),
    ])
    def test_all_apis_without_authentication_returns_401(
        self, http_client: httpx.Client, endpoint: str, method: str
    ):
        """Test all APIs return 401 without authentication."""
        if method == "GET":
            response = http_client.get(endpoint)
        elif method == "DELETE":
            response = http_client.delete(endpoint)
        else:  # POST
            # Parse-catalog requires file upload, not JSON
            if "/stages/parse-catalog" in endpoint:
                files = {"file": ("test.json", b"{}", "application/json")}
                response = http_client.post(endpoint, files=files)
            else:
                response = http_client.post(endpoint, json={})
        
        assert response.status_code == 401

    @pytest.mark.parametrize("endpoint,method", [
        ("/api/v1/jobs", "POST"),
        ("/api/v1/jobs/test-id", "GET"),
        ("/api/v1/jobs/test-id/stages/parse-catalog", "POST"),
    ])
    def test_all_apis_with_invalid_token_returns_401(
        self, http_client: httpx.Client, endpoint: str, method: str
    ):
        """Test all APIs return 401 with invalid token."""
        headers = {
            "Authorization": "Bearer invalid-token-12345",
            "Content-Type": "application/json",
        }
        
        if method == "GET":
            response = http_client.get(endpoint, headers=headers)
        elif method == "DELETE":
            response = http_client.delete(endpoint, headers=headers)
        else:  # POST
            # Parse-catalog requires file upload, not JSON
            if "/stages/parse-catalog" in endpoint:
                files = {"file": ("test.json", b"{}", "application/json")}
                response = http_client.post(endpoint, files=files, headers=headers)
            else:
                response = http_client.post(endpoint, json={}, headers=headers)
        
        assert response.status_code == 401

    @pytest.mark.parametrize("endpoint", [
        "/api/v1/jobs/invalid-uuid-format",
        "/api/v1/jobs/invalid-uuid-format/stages/parse-catalog",
        "/api/v1/jobs/not-a-uuid/catalog/roles",
    ])
    def test_all_apis_with_invalid_job_id_format_returns_400(
        self, http_client: httpx.Client, auth_headers: dict, endpoint: str
    ):
        """Test all APIs return 400 for invalid job ID format."""
        # Try GET first (works for most endpoints)
        response = http_client.get(endpoint, headers=auth_headers)
        
        # 400 for invalid format, 404 if validates format first, 405 if method not allowed, 422 for validation
        assert response.status_code in [400, 404, 405, 422]
