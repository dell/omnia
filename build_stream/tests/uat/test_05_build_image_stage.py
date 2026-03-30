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

"""UAT tests for build-image stage (both x86_64 and aarch64)."""

import time
import httpx
import pytest


@pytest.mark.uat
class TestBuildImageStageSuccess:
    """Test build-image stage success scenarios."""

    def test_build_image_x86_64_after_create_local_repository(
        self, http_client: httpx.Client, auth_headers_with_ids: dict, real_catalog_content: bytes
    ):
        """Test build-image-x86_64 stage after successful create-local-repository."""
        payload = {
            "client_id": "uat-build-image-client",
            "client_name": "UAT Build Image Test",
        }
        
        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]
        
        files = {
            "file": ("catalog.json", sample_catalog_content, "application/json")
        }
        parse_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files=files,
            headers={"Authorization": auth_headers_with_ids["Authorization"]}
        )
        assert parse_response.status_code in [200, 202]
        
        time.sleep(5)
        
        generate_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/generate-input-files",
            headers=auth_headers_with_ids
        )
        assert generate_response.status_code in [200, 202]
        
        time.sleep(5)
        
        repo_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/create-local-repository",
            headers=auth_headers_with_ids
        )
        assert repo_response.status_code in [200, 202]
        
        time.sleep(10)
        
        build_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/build-image-x86_64",
            headers=auth_headers_with_ids
        )
        
        assert build_response.status_code in [200, 202]
        data = build_response.json()
        assert "stage_state" in data
        assert data["stage_state"] in ["RUNNING", "COMPLETED"]

    def test_build_image_aarch64_after_create_local_repository(
        self, http_client: httpx.Client, auth_headers_with_ids: dict, real_catalog_content: bytes
    ):
        """Test build-image-aarch64 stage after successful create-local-repository."""
        payload = {
            "client_id": "uat-build-image-client",
            "client_name": "UAT Build Image Test",
        }
        
        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]
        
        files = {
            "file": ("catalog.json", sample_catalog_content, "application/json")
        }
        parse_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files=files,
            headers={"Authorization": auth_headers_with_ids["Authorization"]}
        )
        assert parse_response.status_code in [200, 202]
        
        time.sleep(5)
        
        generate_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/generate-input-files",
            headers=auth_headers_with_ids
        )
        assert generate_response.status_code in [200, 202]
        
        time.sleep(5)
        
        repo_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/create-local-repository",
            headers=auth_headers_with_ids
        )
        assert repo_response.status_code in [200, 202]
        
        time.sleep(10)
        
        build_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/build-image-aarch64",
            headers=auth_headers_with_ids
        )
        
        assert build_response.status_code in [200, 202]
        data = build_response.json()
        assert "stage_state" in data
        assert data["stage_state"] in ["RUNNING", "COMPLETED"]

    def test_build_image_stage_transitions_to_running(
        self, http_client: httpx.Client, auth_headers_with_ids: dict, real_catalog_content: bytes
    ):
        """Test build-image stage transitions from PENDING to RUNNING."""
        payload = {
            "client_id": "uat-build-image-client",
            "client_name": "UAT Build Image Test",
        }
        
        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]
        
        get_response = http_client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers_with_ids)
        assert get_response.status_code == 200
        stages = get_response.json()["stages"]
        build_stage = next(s for s in stages if s["stage_name"] == "build-image-x86_64")
        assert build_stage["stage_state"] == "PENDING"
        
        files = {
            "file": ("catalog.json", sample_catalog_content, "application/json")
        }
        parse_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files=files,
            headers={"Authorization": auth_headers_with_ids["Authorization"]}
        )
        assert parse_response.status_code in [200, 202]
        
        time.sleep(5)
        
        generate_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/generate-input-files",
            headers=auth_headers_with_ids
        )
        assert generate_response.status_code in [200, 202]
        
        time.sleep(5)
        
        repo_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/create-local-repository",
            headers=auth_headers_with_ids
        )
        assert repo_response.status_code in [200, 202]
        
        time.sleep(10)
        
        build_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/build-image-x86_64",
            headers=auth_headers_with_ids
        )
        
        assert build_response.status_code in [200, 202]
        data = build_response.json()
        assert data["stage_state"] in ["RUNNING", "COMPLETED"]

    def test_build_image_eventually_completes(
        self, http_client: httpx.Client, auth_headers_with_ids: dict, real_catalog_content: bytes
    ):
        """Test build-image stage eventually completes successfully."""
        payload = {
            "client_id": "uat-build-image-client",
            "client_name": "UAT Build Image Test",
        }
        
        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]
        
        files = {
            "file": ("catalog.json", sample_catalog_content, "application/json")
        }
        parse_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files=files,
            headers={"Authorization": auth_headers_with_ids["Authorization"]}
        )
        assert parse_response.status_code in [200, 202]
        
        time.sleep(5)
        
        generate_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/generate-input-files",
            headers=auth_headers_with_ids
        )
        assert generate_response.status_code in [200, 202]
        
        time.sleep(5)
        
        repo_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/create-local-repository",
            headers=auth_headers_with_ids
        )
        assert repo_response.status_code in [200, 202]
        
        time.sleep(10)
        
        build_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/build-image-x86_64",
            headers=auth_headers_with_ids
        )
        assert build_response.status_code in [200, 202]
        
        max_attempts = 120
        for _ in range(max_attempts):
            time.sleep(5)
            get_response = http_client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers_with_ids)
            assert get_response.status_code == 200
            stages = get_response.json()["stages"]
            build_stage = next(s for s in stages if s["stage_name"] == "build-image-x86_64")
            
            if build_stage["stage_state"] in ["COMPLETED", "FAILED"]:
                assert build_stage["stage_state"] == "COMPLETED"
                assert build_stage["started_at"] is not None
                assert build_stage["ended_at"] is not None
                return
        
        pytest.fail("build-image-x86_64 stage did not complete within timeout")


@pytest.mark.uat
class TestBuildImageStageFailure:
    """Test build-image stage failure scenarios."""

    def test_build_image_without_create_local_repository_returns_400(
        self, http_client: httpx.Client, auth_headers_with_ids: dict
    ):
        """Test build-image without create-local-repository returns 400."""
        payload = {
            "client_id": "uat-build-image-client",
            "client_name": "UAT Build Image Test",
        }
        
        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]
        
        build_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/build-image-x86_64",
            headers=auth_headers_with_ids
        )
        
        assert build_response.status_code in [400, 409]

    def test_build_image_for_nonexistent_job_returns_404(
        self, http_client: httpx.Client, auth_headers_with_ids: dict
    ):
        """Test build-image for nonexistent job returns 404."""
        import uuid
        nonexistent_job_id = str(uuid.uuid4())
        
        build_response = http_client.post(
            f"/api/v1/jobs/{nonexistent_job_id}/stages/build-image-x86_64",
            headers=auth_headers_with_ids
        )
        
        assert build_response.status_code == 404

    def test_build_image_without_auth_returns_401(self, http_client: httpx.Client):
        """Test build-image without authentication returns 401."""
        import uuid
        job_id = str(uuid.uuid4())
        
        build_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/build-image-x86_64"
        )
        
        assert build_response.status_code == 401

    def test_build_image_with_invalid_job_id_returns_422(
        self, http_client: httpx.Client, auth_headers_with_ids: dict
    ):
        """Test build-image with invalid job ID format returns 422."""
        invalid_job_id = "not-a-valid-uuid"
        
        build_response = http_client.post(
            f"/api/v1/jobs/{invalid_job_id}/stages/build-image-x86_64",
            headers=auth_headers_with_ids
        )
        
        assert build_response.status_code == 422

    def test_build_image_twice_returns_409(
        self, http_client: httpx.Client, auth_headers_with_ids: dict, real_catalog_content: bytes
    ):
        """Test build-image executed twice returns 409."""
        payload = {
            "client_id": "uat-build-image-client",
            "client_name": "UAT Build Image Test",
        }
        
        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]
        
        files = {
            "file": ("catalog.json", sample_catalog_content, "application/json")
        }
        parse_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files=files,
            headers={"Authorization": auth_headers_with_ids["Authorization"]}
        )
        assert parse_response.status_code in [200, 202]
        
        time.sleep(5)
        
        generate_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/generate-input-files",
            headers=auth_headers_with_ids
        )
        assert generate_response.status_code in [200, 202]
        
        time.sleep(5)
        
        repo_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/create-local-repository",
            headers=auth_headers_with_ids
        )
        assert repo_response.status_code in [200, 202]
        
        time.sleep(10)
        
        first_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/build-image-x86_64",
            headers=auth_headers_with_ids
        )
        assert first_response.status_code in [200, 202]
        
        time.sleep(2)
        
        second_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/build-image-x86_64",
            headers=auth_headers_with_ids
        )
        
        assert second_response.status_code == 409

    def test_build_image_with_invalid_architecture_returns_404(
        self, http_client: httpx.Client, auth_headers_with_ids: dict
    ):
        """Test build-image with invalid architecture returns 404."""
        payload = {
            "client_id": "uat-build-image-client",
            "client_name": "UAT Build Image Test",
        }
        
        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]
        
        build_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/build-image-invalid-arch",
            headers=auth_headers_with_ids
        )
        
        assert build_response.status_code == 404
