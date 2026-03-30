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

"""UAT tests for parse-catalog stage."""

import json
import time
import httpx
import pytest


@pytest.mark.uat
class TestParseCatalogStageSuccess:
    """Test parse-catalog stage success scenarios."""

    def test_parse_catalog_with_valid_file(
        self, http_client: httpx.Client, auth_headers_with_ids: dict, real_catalog_content: bytes
    ):
        """Test parse-catalog stage with valid catalog file."""
        payload = {
            "client_id": "uat-parse-catalog-client",
            "client_name": "UAT Parse Catalog Test",
        }
        
        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]
        
        files = {
            "file": ("catalog.json", real_catalog_content, "application/json")
        }
        
        stage_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files=files,
            headers={"Authorization": auth_headers_with_ids["Authorization"]}
        )
        
        assert stage_response.status_code in [200, 202]
        data = stage_response.json()
        assert "status" in data
        assert data["status"] == "success"

    def test_parse_catalog_stage_transitions_to_running(
        self, http_client: httpx.Client, auth_headers_with_ids: dict, real_catalog_content: bytes
    ):
        """Test parse-catalog stage transitions from PENDING to RUNNING."""
        payload = {
            "client_id": "uat-parse-catalog-client",
            "client_name": "UAT Parse Catalog Test",
        }
        
        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]
        
        get_response = http_client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers_with_ids)
        assert get_response.status_code == 200
        stages = get_response.json()["stages"]
        parse_stage = next(s for s in stages if s["stage_name"] == "parse-catalog")
        assert parse_stage["stage_state"] == "PENDING"
        
        files = {
            "file": ("catalog.json", real_catalog_content, "application/json")
        }
        
        stage_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files=files,
            headers={"Authorization": auth_headers_with_ids["Authorization"]}
        )
        
        assert stage_response.status_code in [200, 202]
        data = stage_response.json()
        assert "status" in data
        assert data["status"] == "success"

    def test_parse_catalog_stage_eventually_completes(
        self, http_client: httpx.Client, auth_headers_with_ids: dict, real_catalog_content: bytes
    ):
        """Test parse-catalog stage eventually completes successfully."""
        payload = {
            "client_id": "uat-parse-catalog-client",
            "client_name": "UAT Parse Catalog Test",
        }
        
        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]
        
        files = {
            "file": ("catalog.json", real_catalog_content, "application/json")
        }
        
        stage_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files=files,
            headers={"Authorization": auth_headers_with_ids["Authorization"]}
        )
        
        assert stage_response.status_code in [200, 202]
        
        max_attempts = 30
        for _ in range(max_attempts):
            time.sleep(2)
            get_response = http_client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers_with_ids)
            assert get_response.status_code == 200
            stages = get_response.json()["stages"]
            parse_stage = next(s for s in stages if s["stage_name"] == "parse-catalog")
            
            if parse_stage["stage_state"] in ["COMPLETED", "FAILED"]:
                assert parse_stage["stage_state"] == "COMPLETED"
                assert parse_stage["started_at"] is not None
                assert parse_stage["ended_at"] is not None
                return
        
        pytest.fail("parse-catalog stage did not complete within timeout")


@pytest.mark.uat
class TestParseCatalogStageFailure:
    """Test parse-catalog stage failure scenarios."""

    def test_parse_catalog_without_file_returns_400(
        self, http_client: httpx.Client, auth_headers_with_ids: dict
    ):
        """Test parse-catalog without catalog file returns 400."""
        payload = {
            "client_id": "uat-parse-catalog-client",
            "client_name": "UAT Parse Catalog Test",
        }
        
        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]
        
        stage_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            headers=auth_headers_with_ids
        )
        
        assert stage_response.status_code == 422

    def test_parse_catalog_with_invalid_json_returns_400(
        self, http_client: httpx.Client, auth_headers_with_ids: dict
    ):
        """Test parse-catalog with invalid JSON returns 400."""
        payload = {
            "client_id": "uat-parse-catalog-client",
            "client_name": "UAT Parse Catalog Test",
        }
        
        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]
        
        invalid_content = b"{ invalid json content"
        files = {
            "catalog": ("catalog.json", invalid_content, "application/json")
        }
        
        stage_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files=files,
            headers={"Authorization": auth_headers_with_ids["Authorization"]}
        )
        
        assert stage_response.status_code in [400, 422]

    
    def test_parse_catalog_for_nonexistent_job_returns_404(
        self, http_client: httpx.Client, auth_headers_with_ids: dict, real_catalog_content: bytes
    ):
        """Test parse-catalog for nonexistent job returns 404."""
        import uuid
        nonexistent_job_id = str(uuid.uuid4())
        
        files = {
            "file": ("catalog.json", real_catalog_content, "application/json")
        }
        
        stage_response = http_client.post(
            f"/api/v1/jobs/{nonexistent_job_id}/stages/parse-catalog",
            files=files,
            headers={"Authorization": auth_headers_with_ids["Authorization"]}
        )
        
        assert stage_response.status_code == 404

    def test_parse_catalog_without_auth_returns_401(
        self, http_client: httpx.Client, real_catalog_content: bytes
    ):
        """Test parse-catalog without authentication returns 401."""
        import uuid
        job_id = str(uuid.uuid4())
        
        files = {
            "file": ("catalog.json", real_catalog_content, "application/json")
        }
        
        stage_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files=files
        )
        
        assert stage_response.status_code == 401

    def test_parse_catalog_with_wrong_content_type_returns_400(
        self, http_client: httpx.Client, auth_headers_with_ids: dict
    ):
        """Test parse-catalog with wrong content type returns 400."""
        payload = {
            "client_id": "uat-parse-catalog-client",
            "client_name": "UAT Parse Catalog Test",
        }
        
        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]
        
        files = {
            "file": ("catalog.txt", b"not a json file", "text/plain")
        }
        
        stage_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files=files,
            headers={"Authorization": auth_headers_with_ids["Authorization"]}
        )
        
        assert stage_response.status_code in [400, 422]

    def test_parse_catalog_with_empty_file_returns_400(
        self, http_client: httpx.Client, auth_headers_with_ids: dict
    ):
        """Test parse-catalog with empty file returns 400."""
        payload = {
            "client_id": "uat-parse-catalog-client",
            "client_name": "UAT Parse Catalog Test",
        }
        
        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]
        
        files = {
            "catalog": ("catalog.json", b"", "application/json")
        }
        
        stage_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files=files,
            headers={"Authorization": auth_headers_with_ids["Authorization"]}
        )
        
        assert stage_response.status_code in [400, 422]
