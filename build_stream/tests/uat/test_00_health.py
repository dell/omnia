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

"""UAT tests for health check and basic connectivity."""

import httpx
import pytest


@pytest.mark.uat
class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_endpoint_returns_200(self, http_client: httpx.Client):
        """Test health endpoint returns 200 OK."""
        response = http_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_health_endpoint_is_reachable(self, http_client: httpx.Client):
        """Test server is reachable and responding."""
        try:
            response = http_client.get("/health")
            assert response.status_code == 200
        except httpx.RequestError as e:
            pytest.fail(f"Server is not reachable: {e}")


@pytest.mark.uat
class TestRootEndpoint:
    """Test root endpoint."""

    def test_root_endpoint_returns_200(self, http_client: httpx.Client):
        """Test root endpoint returns 200 OK."""
        response = http_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "docs" in data
        assert "version" in data

    def test_root_endpoint_returns_welcome_message(self, http_client: httpx.Client):
        """Test root endpoint returns welcome message."""
        response = http_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "Build Stream" in data["message"]
        assert data["docs"] == "/docs"
