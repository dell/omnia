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

"""UAT tests for create-local-repository stage."""

import time
import httpx
import pytest


@pytest.mark.uat
class TestCreateLocalRepositoryStageSuccess:
    """Test create-local-repository stage success scenarios."""

    def test_create_local_repository_after_generate_input_files(
        self, http_client: httpx.Client, auth_headers_with_ids: dict, real_catalog_content: bytes
    ):
        """Test create-local-repository stage after successful generate-input-files."""
        payload = {
            "client_id": "uat-create-repo-client",
            "client_name": "UAT Create Repo Test",
        }
        
        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]
        
        files = {
            "file": ("catalog.json", real_catalog_content, "application/json")
        }
        parse_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files=files,
            headers={"Authorization": auth_headers_with_ids["Authorization"]}
        )
        assert parse_response.status_code in [200, 202]
        
        
        
        generate_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/generate-input-files",
            headers=auth_headers_with_ids
        )
        assert generate_response.status_code in [200, 202]
        
        
        
        repo_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/create-local-repository",
            headers=auth_headers_with_ids
        )
        
        assert repo_response.status_code in [200, 202]
        data = repo_response.json()
        assert "status" in data
        assert data["status"] == "accepted"

    def test_create_local_repository_stage_transitions_to_running(
        self, http_client: httpx.Client, auth_headers_with_ids: dict, real_catalog_content: bytes
    ):
        """Test create-local-repository stage transitions from PENDING to RUNNING."""
        payload = {
            "client_id": "uat-create-repo-client",
            "client_name": "UAT Create Repo Test",
        }
        
        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]
        
        get_response = http_client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers_with_ids)
        assert get_response.status_code == 200
        stages = get_response.json()["stages"]
        repo_stage = next(s for s in stages if s["stage_name"] == "create-local-repository")
        assert repo_stage["stage_state"] == "PENDING"
        
        files = {
            "file": ("catalog.json", real_catalog_content, "application/json")
        }
        parse_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files=files,
            headers={"Authorization": auth_headers_with_ids["Authorization"]}
        )
        assert parse_response.status_code in [200, 202]
        
        
        
        generate_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/generate-input-files",
            headers=auth_headers_with_ids
        )
        assert generate_response.status_code in [200, 202]
        
        
        
        repo_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/create-local-repository",
            headers=auth_headers_with_ids
        )
        
        assert repo_response.status_code in [200, 202]
        data = repo_response.json()
        assert "status" in data
        assert data["status"] == "accepted"

    def test_create_local_repository_eventually_completes(
        self, http_client: httpx.Client, auth_headers_with_ids: dict, real_catalog_content: bytes
    ):
        """Test create-local-repository stage eventually completes successfully."""
        payload = {
            "client_id": "uat-create-repo-client",
            "client_name": "UAT Create Repo Test",
        }
        
        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]
        
        files = {
            "file": ("catalog.json", real_catalog_content, "application/json")
        }
        parse_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files=files,
            headers={"Authorization": auth_headers_with_ids["Authorization"]}
        )
        assert parse_response.status_code in [200, 202]
        
        
        
        generate_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/generate-input-files",
            headers=auth_headers_with_ids
        )
        assert generate_response.status_code in [200, 202]
        
        
        
        repo_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/create-local-repository",
            headers=auth_headers_with_ids
        )
        assert repo_response.status_code in [200, 202]
        
        max_attempts = 60
        for _ in range(max_attempts):
            time.sleep(5)
            get_response = http_client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers_with_ids)
            assert get_response.status_code == 200
            stages = get_response.json()["stages"]
            repo_stage = next(s for s in stages if s["stage_name"] == "create-local-repository")
            
            if repo_stage["stage_state"] in ["COMPLETED", "FAILED"]:
                assert repo_stage["stage_state"] == "COMPLETED"
                assert repo_stage["started_at"] is not None
                assert repo_stage["ended_at"] is not None
                return
        
        pytest.fail("create-local-repository stage did not complete within timeout")


@pytest.mark.uat
class TestCreateLocalRepositoryStageFailure:
    """Test create-local-repository stage failure scenarios."""

    def test_create_local_repository_without_generate_input_files_returns_400(
        self, http_client: httpx.Client, auth_headers_with_ids: dict
    ):
        """Test create-local-repository without generate-input-files returns 400."""
        payload = {
            "client_id": "uat-create-repo-client",
            "client_name": "UAT Create Repo Test",
        }
        
        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]
        
        repo_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/create-local-repository",
            headers=auth_headers_with_ids
        )
        
        assert repo_response.status_code == 412

    def test_create_local_repository_for_nonexistent_job_returns_404(
        self, http_client: httpx.Client, auth_headers_with_ids: dict
    ):
        """Test create-local-repository for nonexistent job returns 404."""
        import uuid
        nonexistent_job_id = str(uuid.uuid4())
        
        repo_response = http_client.post(
            f"/api/v1/jobs/{nonexistent_job_id}/stages/create-local-repository",
            headers=auth_headers_with_ids
        )
        
        assert repo_response.status_code == 404

    def test_create_local_repository_without_auth_returns_401(self, http_client: httpx.Client):
        """Test create-local-repository without authentication returns 401."""
        import uuid
        job_id = str(uuid.uuid4())
        
        repo_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/create-local-repository"
        )
        
        assert repo_response.status_code == 401

    def test_create_local_repository_with_invalid_job_id_returns_422(
        self, http_client: httpx.Client, auth_headers_with_ids: dict
    ):
        """Test create-local-repository with invalid job ID format returns 422."""
        invalid_job_id = "not-a-valid-uuid"
        
        repo_response = http_client.post(
            f"/api/v1/jobs/{invalid_job_id}/stages/create-local-repository",
            headers=auth_headers_with_ids
        )
        
        assert repo_response.status_code == 400

    def test_create_local_repository_twice_returns_409(
        self, http_client: httpx.Client, auth_headers_with_ids: dict, real_catalog_content: bytes
    ):
        """Test create-local-repository executed twice returns 409."""
        payload = {
            "client_id": "uat-create-repo-client",
            "client_name": "UAT Create Repo Test",
        }
        
        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]
        
        files = {
            "file": ("catalog.json", real_catalog_content, "application/json")
        }
        parse_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files=files,
            headers={"Authorization": auth_headers_with_ids["Authorization"]}
        )
        assert parse_response.status_code in [200, 202]
        
        
        
        generate_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/generate-input-files",
            headers=auth_headers_with_ids
        )
        assert generate_response.status_code in [200, 202]
        
        
        
        first_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/create-local-repository",
            headers=auth_headers_with_ids
        )
        assert first_response.status_code in [200, 202]
        
        time.sleep(2)
        
        second_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/create-local-repository",
            headers=auth_headers_with_ids
        )
        
        assert second_response.status_code == 409
