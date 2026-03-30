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

"""UAT tests for validate-image-on-test stage."""

import time
import httpx
import pytest


@pytest.mark.uat
class TestValidateImageOnTestStageSuccess:
    """Test validate-image-on-test stage success scenarios."""

    def test_validate_image_after_build_image(
        self, http_client: httpx.Client, auth_headers_with_ids: dict, real_catalog_content: bytes
    ):
        """Test validate-image-on-test stage after successful build-image."""
        payload = {
            "client_id": "uat-validate-image-client",
            "client_name": "UAT Validate Image Test",
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
        
        time.sleep(15)
        
        validate_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/validate-image-on-test",
            headers=auth_headers_with_ids
        )
        
        assert validate_response.status_code in [200, 202]
        data = validate_response.json()
        assert "stage_state" in data
        assert data["stage_state"] in ["RUNNING", "COMPLETED"]

    def test_validate_image_stage_transitions_to_running(
        self, http_client: httpx.Client, auth_headers_with_ids: dict, real_catalog_content: bytes
    ):
        """Test validate-image-on-test stage transitions from PENDING to RUNNING."""
        payload = {
            "client_id": "uat-validate-image-client",
            "client_name": "UAT Validate Image Test",
        }
        
        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]
        
        get_response = http_client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers_with_ids)
        assert get_response.status_code == 200
        stages = get_response.json()["stages"]
        validate_stage = next(s for s in stages if s["stage_name"] == "validate-image-on-test")
        assert validate_stage["stage_state"] == "PENDING"
        
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
        
        time.sleep(15)
        
        validate_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/validate-image-on-test",
            headers=auth_headers_with_ids
        )
        
        assert validate_response.status_code in [200, 202]
        data = validate_response.json()
        assert data["stage_state"] in ["RUNNING", "COMPLETED"]

    def test_validate_image_eventually_completes(
        self, http_client: httpx.Client, auth_headers_with_ids: dict, real_catalog_content: bytes
    ):
        """Test validate-image-on-test stage eventually completes successfully."""
        payload = {
            "client_id": "uat-validate-image-client",
            "client_name": "UAT Validate Image Test",
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
        
        time.sleep(15)
        
        validate_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/validate-image-on-test",
            headers=auth_headers_with_ids
        )
        assert validate_response.status_code in [200, 202]
        
        max_attempts = 60
        for _ in range(max_attempts):
            time.sleep(5)
            get_response = http_client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers_with_ids)
            assert get_response.status_code == 200
            stages = get_response.json()["stages"]
            validate_stage = next(s for s in stages if s["stage_name"] == "validate-image-on-test")
            
            if validate_stage["stage_state"] in ["COMPLETED", "FAILED"]:
                assert validate_stage["stage_state"] == "COMPLETED"
                assert validate_stage["started_at"] is not None
                assert validate_stage["ended_at"] is not None
                return
        
        pytest.fail("validate-image-on-test stage did not complete within timeout")


@pytest.mark.uat
class TestValidateImageOnTestStageFailure:
    """Test validate-image-on-test stage failure scenarios."""

    def test_validate_image_without_build_image_returns_400(
        self, http_client: httpx.Client, auth_headers_with_ids: dict
    ):
        """Test validate-image-on-test without build-image returns 400."""
        payload = {
            "client_id": "uat-validate-image-client",
            "client_name": "UAT Validate Image Test",
        }
        
        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]
        
        validate_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/validate-image-on-test",
            headers=auth_headers_with_ids
        )
        
        assert validate_response.status_code in [400, 409]

    def test_validate_image_for_nonexistent_job_returns_404(
        self, http_client: httpx.Client, auth_headers_with_ids: dict
    ):
        """Test validate-image-on-test for nonexistent job returns 404."""
        import uuid
        nonexistent_job_id = str(uuid.uuid4())
        
        validate_response = http_client.post(
            f"/api/v1/jobs/{nonexistent_job_id}/stages/validate-image-on-test",
            headers=auth_headers_with_ids
        )
        
        assert validate_response.status_code == 404

    def test_validate_image_without_auth_returns_401(self, http_client: httpx.Client):
        """Test validate-image-on-test without authentication returns 401."""
        import uuid
        job_id = str(uuid.uuid4())
        
        validate_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/validate-image-on-test"
        )
        
        assert validate_response.status_code == 401

    def test_validate_image_with_invalid_job_id_returns_422(
        self, http_client: httpx.Client, auth_headers_with_ids: dict
    ):
        """Test validate-image-on-test with invalid job ID format returns 422."""
        invalid_job_id = "not-a-valid-uuid"
        
        validate_response = http_client.post(
            f"/api/v1/jobs/{invalid_job_id}/stages/validate-image-on-test",
            headers=auth_headers_with_ids
        )
        
        assert validate_response.status_code == 422

    def test_validate_image_twice_returns_409(
        self, http_client: httpx.Client, auth_headers_with_ids: dict, real_catalog_content: bytes
    ):
        """Test validate-image-on-test executed twice returns 409."""
        payload = {
            "client_id": "uat-validate-image-client",
            "client_name": "UAT Validate Image Test",
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
        
        time.sleep(15)
        
        first_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/validate-image-on-test",
            headers=auth_headers_with_ids
        )
        assert first_response.status_code in [200, 202]
        
        time.sleep(2)
        
        second_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/validate-image-on-test",
            headers=auth_headers_with_ids
        )
        
        assert second_response.status_code == 409
