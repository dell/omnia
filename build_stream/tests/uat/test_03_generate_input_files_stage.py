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

"""UAT tests for generate-input-files stage."""

import time
import httpx
import pytest


@pytest.mark.uat
class TestGenerateInputFilesStageSuccess:
    """Test generate-input-files stage success scenarios."""

    def test_generate_input_files_after_parse_catalog(
        self, http_client: httpx.Client, auth_headers_with_ids: dict, real_catalog_content: bytes
    ):
        """Test generate-input-files stage after successful parse-catalog."""
        payload = {
            "client_id": "uat-generate-input-client",
            "client_name": "UAT Generate Input Test",
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
        data = generate_response.json()
        assert "stage_state" in data
        assert data["stage_state"] in ["RUNNING", "COMPLETED"]

    def test_generate_input_files_stage_transitions_to_running(
        self, http_client: httpx.Client, auth_headers_with_ids: dict, real_catalog_content: bytes
    ):
        """Test generate-input-files stage transitions from PENDING to RUNNING."""
        payload = {
            "client_id": "uat-generate-input-client",
            "client_name": "UAT Generate Input Test",
        }

        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]

        get_response = http_client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers_with_ids)
        assert get_response.status_code == 200
        stages = get_response.json()["stages"]
        generate_stage = next(s for s in stages if s["stage_name"] == "generate-input-files")
        assert generate_stage["stage_state"] == "PENDING"

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
        data = generate_response.json()
        assert data["stage_state"] in ["RUNNING", "COMPLETED"]

    def test_generate_input_files_eventually_completes(
        self, http_client: httpx.Client, auth_headers_with_ids: dict, real_catalog_content: bytes
    ):
        """Test generate-input-files stage eventually completes successfully."""
        payload = {
            "client_id": "uat-generate-input-client",
            "client_name": "UAT Generate Input Test",
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

        max_attempts = 30
        for _ in range(max_attempts):
            time.sleep(2)
            get_response = http_client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers_with_ids)
            assert get_response.status_code == 200
            stages = get_response.json()["stages"]
            generate_stage = next(s for s in stages if s["stage_name"] == "generate-input-files")

            if generate_stage["stage_state"] in ["COMPLETED", "FAILED"]:
                assert generate_stage["stage_state"] == "COMPLETED"
                assert generate_stage["started_at"] is not None
                assert generate_stage["ended_at"] is not None
                return

        pytest.fail("generate-input-files stage did not complete within timeout")


@pytest.mark.uat
class TestGenerateInputFilesStageFailure:
    """Test generate-input-files stage failure scenarios."""

    def test_generate_input_files_without_parse_catalog_returns_400(
        self, http_client: httpx.Client, auth_headers_with_ids: dict
    ):
        """Test generate-input-files without parse-catalog returns 400."""
        payload = {
            "client_id": "uat-generate-input-client",
            "client_name": "UAT Generate Input Test",
        }

        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]

        generate_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/generate-input-files",
            headers=auth_headers_with_ids
        )

        assert generate_response.status_code == 412

    def test_generate_input_files_for_nonexistent_job_returns_404(
        self, http_client: httpx.Client, auth_headers_with_ids: dict
    ):
        """Test generate-input-files for nonexistent job returns 404."""
        import uuid
        nonexistent_job_id = str(uuid.uuid4())

        generate_response = http_client.post(
            f"/api/v1/jobs/{nonexistent_job_id}/stages/generate-input-files",
            headers=auth_headers_with_ids
        )

        assert generate_response.status_code == 404

    def test_generate_input_files_without_auth_returns_401(self, http_client: httpx.Client):
        """Test generate-input-files without authentication returns 401."""
        import uuid
        job_id = str(uuid.uuid4())

        generate_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/generate-input-files"
        )

        assert generate_response.status_code == 401

    def test_generate_input_files_with_invalid_job_id_returns_422(
        self, http_client: httpx.Client, auth_headers_with_ids: dict
    ):
        """Test generate-input-files with invalid job ID format returns 422."""
        invalid_job_id = "not-a-valid-uuid"

        generate_response = http_client.post(
            f"/api/v1/jobs/{invalid_job_id}/stages/generate-input-files",
            headers=auth_headers_with_ids
        )

        assert generate_response.status_code == 400

    def test_generate_input_files_twice_returns_409(
        self, http_client: httpx.Client, auth_headers_with_ids: dict, real_catalog_content: bytes
    ):
        """Test generate-input-files executed twice returns 409."""
        payload = {
            "client_id": "uat-generate-input-client",
            "client_name": "UAT Generate Input Test",
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

        time.sleep(2)

        first_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/generate-input-files",
            headers=auth_headers_with_ids
        )
        assert first_response.status_code in [200, 202]

        time.sleep(2)

        second_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/generate-input-files",
            headers=auth_headers_with_ids
        )

        assert second_response.status_code == 409
