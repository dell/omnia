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

"""Integration tests for Restart API."""

import pytest


class TestRestartAPI:
    """Integration tests for restart API endpoints."""

    def test_create_restart_success(self, client, auth_headers, job_with_pending_restart):
        """Test successful restart creation."""
        job_id = job_with_pending_restart

        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/restart",
            headers=auth_headers
        )

        assert response.status_code == 202
        data = response.json()
        assert data["job_id"] == job_id
        assert data["stage"] == "restart"
        assert data["status"] == "accepted"
        assert "correlation_id" in data
        assert "submitted_at" in data
        assert "image_group_id" in data

    def test_create_restart_has_links(self, client, auth_headers, job_with_pending_restart):
        """Test that restart response includes HATEOAS _links."""
        job_id = job_with_pending_restart

        response = client.post(
            f"/api/v1/jobs/{job_id}/stages/restart",
            headers=auth_headers
        )

        assert response.status_code == 202
        data = response.json()
        assert "_links" in data
        assert "self" in data["_links"]
        assert "status" in data["_links"]
        assert job_id in data["_links"]["self"]

    def test_create_restart_unauthorized(self, client):
        """Test restart creation without authorization."""
        response = client.post(
            "/api/v1/jobs/test-job/stages/restart",
        )
        assert response.status_code in [400, 401]

    def test_create_restart_invalid_job_id(self, client, auth_headers):
        """Test restart creation with invalid job ID format."""
        response = client.post(
            "/api/v1/jobs/not-a-valid-uuid/stages/restart",
            headers=auth_headers
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_create_restart_job_not_found(self, client, auth_headers):
        """Test restart creation for non-existent job."""
        import uuid
        fake_job_id = str(uuid.uuid4())

        response = client.post(
            f"/api/v1/jobs/{fake_job_id}/stages/restart",
            headers=auth_headers
        )
        # Should get 400 for invalid job_id format or 404 for not found
        assert response.status_code in [400, 404]
        data = response.json()
        assert "detail" in data
