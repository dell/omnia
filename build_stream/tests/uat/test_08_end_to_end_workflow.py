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

"""UAT tests for end-to-end workflow (sequential stage execution)."""

import json
import time
import httpx
import pytest


@pytest.mark.uat
@pytest.mark.slow
class TestEndToEndWorkflow:
    """Test complete end-to-end workflow execution."""

    def test_complete_workflow_sequential_execution(
        self, http_client: httpx.Client, auth_headers_with_ids: dict
    ):
        """Test complete workflow from job creation to final validation."""
        catalog_data = {
            "metadata": {
                "name": "e2e-test-catalog",
                "version": "1.0.0",
                "description": "End-to-end test catalog",
            },
            "software": [
                {
                    "name": "test-package",
                    "version": "1.0.0",
                    "arch": "x86_64",
                    "repository": "test-repo",
                }
            ],
        }
        catalog_content = json.dumps(catalog_data, indent=2).encode('utf-8')
        
        payload = {
            "client_id": "uat-e2e-client",
            "client_name": "UAT E2E Test",
        }
        
        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]
        print(f"\n✓ Job created: {job_id}")
        
        files = {
            "file": ("catalog.json", catalog_content, "application/json")
        }
        
        parse_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files=files,
            headers={"Authorization": auth_headers_with_ids["Authorization"]}
        )
        assert parse_response.status_code in [200, 202]
        print("✓ Parse-catalog stage initiated")
        
        self._wait_for_stage_completion(http_client, job_id, "parse-catalog", auth_headers_with_ids, max_wait=60)
        print("✓ Parse-catalog stage completed")
        
        generate_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/generate-input-files",
            headers=auth_headers_with_ids
        )
        assert generate_response.status_code in [200, 202]
        print("✓ Generate-input-files stage initiated")
        
        self._wait_for_stage_completion(http_client, job_id, "generate-input-files", auth_headers_with_ids, max_wait=60)
        print("✓ Generate-input-files stage completed")
        
        repo_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/create-local-repository",
            headers=auth_headers_with_ids
        )
        assert repo_response.status_code in [200, 202]
        print("✓ Create-local-repository stage initiated")
        
        self._wait_for_stage_completion(http_client, job_id, "create-local-repository", auth_headers_with_ids, max_wait=300)
        print("✓ Create-local-repository stage completed")
        
        build_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/build-image-x86_64",
            headers=auth_headers_with_ids
        )
        assert build_response.status_code in [200, 202]
        print("✓ Build-image-x86_64 stage initiated")
        
        self._wait_for_stage_completion(http_client, job_id, "build-image-x86_64", auth_headers_with_ids, max_wait=600)
        print("✓ Build-image-x86_64 stage completed")
        
        validate_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/validate-image-on-test",
            headers=auth_headers_with_ids
        )
        assert validate_response.status_code in [200, 202]
        print("✓ Validate-image-on-test stage initiated")
        
        self._wait_for_stage_completion(http_client, job_id, "validate-image-on-test", auth_headers_with_ids, max_wait=300)
        print("✓ Validate-image-on-test stage completed")
        
        final_response = http_client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers_with_ids)
        assert final_response.status_code == 200
        final_data = final_response.json()
        
        assert final_data["job_state"] in ["COMPLETED", "RUNNING"]
        print(f"✓ Final job state: {final_data['job_state']}")
        
        stages = final_data["stages"]
        completed_stages = [s for s in stages if s["stage_state"] == "COMPLETED"]
        assert len(completed_stages) >= 5
        print(f"✓ Completed stages: {len(completed_stages)}/6")

    def test_workflow_with_both_architectures(
        self, http_client: httpx.Client, auth_headers_with_ids: dict
    ):
        """Test workflow executing both x86_64 and aarch64 build stages."""
        catalog_data = {
            "metadata": {
                "name": "multi-arch-catalog",
                "version": "1.0.0",
                "description": "Multi-architecture test catalog",
            },
            "software": [
                {
                    "name": "test-package-x86",
                    "version": "1.0.0",
                    "arch": "x86_64",
                    "repository": "test-repo",
                },
                {
                    "name": "test-package-arm",
                    "version": "1.0.0",
                    "arch": "aarch64",
                    "repository": "test-repo",
                }
            ],
        }
        catalog_content = json.dumps(catalog_data, indent=2).encode('utf-8')
        
        payload = {
            "client_id": "uat-e2e-multi-arch-client",
            "client_name": "UAT E2E Multi-Arch Test",
        }
        
        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]
        print(f"\n✓ Job created: {job_id}")
        
        files = {
            "file": ("catalog.json", catalog_content, "application/json")
        }
        
        parse_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files=files,
            headers={"Authorization": auth_headers_with_ids["Authorization"]}
        )
        assert parse_response.status_code in [200, 202]
        
        self._wait_for_stage_completion(http_client, job_id, "parse-catalog", auth_headers_with_ids, max_wait=60)
        
        generate_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/generate-input-files",
            headers=auth_headers_with_ids
        )
        assert generate_response.status_code in [200, 202]
        
        self._wait_for_stage_completion(http_client, job_id, "generate-input-files", auth_headers_with_ids, max_wait=60)
        
        repo_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/create-local-repository",
            headers=auth_headers_with_ids
        )
        assert repo_response.status_code in [200, 202]
        
        self._wait_for_stage_completion(http_client, job_id, "create-local-repository", auth_headers_with_ids, max_wait=300)
        
        build_x86_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/build-image-x86_64",
            headers=auth_headers_with_ids
        )
        assert build_x86_response.status_code in [200, 202]
        print("✓ Build-image-x86_64 stage initiated")
        
        build_arm_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/build-image-aarch64",
            headers=auth_headers_with_ids
        )
        assert build_arm_response.status_code in [200, 202]
        print("✓ Build-image-aarch64 stage initiated")
        
        self._wait_for_stage_completion(http_client, job_id, "build-image-x86_64", auth_headers_with_ids, max_wait=600)
        print("✓ Build-image-x86_64 stage completed")
        
        self._wait_for_stage_completion(http_client, job_id, "build-image-aarch64", auth_headers_with_ids, max_wait=600)
        print("✓ Build-image-aarch64 stage completed")

    def test_workflow_stage_dependencies(
        self, http_client: httpx.Client, auth_headers_with_ids: dict
    ):
        """Test that stages enforce proper dependencies."""
        payload = {
            "client_id": "uat-e2e-dependencies-client",
            "client_name": "UAT E2E Dependencies Test",
        }
        
        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]
        
        generate_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/generate-input-files",
            headers=auth_headers_with_ids
        )
        assert generate_response.status_code in [400, 409]
        print("✓ Generate-input-files correctly rejected without parse-catalog")
        
        repo_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/create-local-repository",
            headers=auth_headers_with_ids
        )
        assert repo_response.status_code in [400, 409]
        print("✓ Create-local-repository correctly rejected without generate-input-files")
        
        build_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/build-image-x86_64",
            headers=auth_headers_with_ids
        )
        assert build_response.status_code in [400, 409]
        print("✓ Build-image correctly rejected without create-local-repository")
        
        validate_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/validate-image-on-test",
            headers=auth_headers_with_ids
        )
        assert validate_response.status_code in [400, 409]
        print("✓ Validate-image correctly rejected without build-image")

    def test_workflow_with_catalog_query(
        self, http_client: httpx.Client, auth_headers_with_ids: dict
    ):
        """Test workflow with catalog query after parse stage."""
        catalog_data = {
            "metadata": {
                "name": "query-workflow-catalog",
                "version": "1.0.0",
                "description": "Catalog for query workflow test",
            },
            "software": [
                {
                    "name": "queryable-package",
                    "version": "1.0.0",
                    "arch": "x86_64",
                    "repository": "test-repo",
                }
            ],
        }
        catalog_content = json.dumps(catalog_data, indent=2).encode('utf-8')
        
        payload = {
            "client_id": "uat-e2e-query-client",
            "client_name": "UAT E2E Query Test",
        }
        
        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]
        
        files = {
            "file": ("catalog.json", catalog_content, "application/json")
        }
        
        parse_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files=files,
            headers={"Authorization": auth_headers_with_ids["Authorization"]}
        )
        assert parse_response.status_code in [200, 202]
        
        self._wait_for_stage_completion(http_client, job_id, "parse-catalog", auth_headers_with_ids, max_wait=60)
        
        query_response = http_client.get(
            f"/api/v1/jobs/{job_id}/catalog",
            headers=auth_headers_with_ids
        )
        assert query_response.status_code == 200
        print("✓ Catalog query successful after parse-catalog")
        
        query_data = query_response.json()
        assert isinstance(query_data, dict)
        print(f"✓ Catalog data retrieved: {len(str(query_data))} bytes")

    def _wait_for_stage_completion(
        self, http_client: httpx.Client, job_id: str, stage_name: str, 
        auth_headers: dict, max_wait: int = 60
    ):
        """Wait for a stage to complete with timeout."""
        attempts = max_wait // 5
        for attempt in range(attempts):
            time.sleep(5)
            get_response = http_client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers)
            if get_response.status_code != 200:
                continue
            
            stages = get_response.json()["stages"]
            stage = next((s for s in stages if s["stage_name"] == stage_name), None)
            
            if stage and stage["stage_state"] == "COMPLETED":
                return
            
            if stage and stage["stage_state"] == "FAILED":
                pytest.fail(f"Stage {stage_name} failed")
            
            if attempt % 6 == 0:
                print(f"  Waiting for {stage_name}... ({attempt * 5}s elapsed)")
        
        pytest.fail(f"Stage {stage_name} did not complete within {max_wait}s")


@pytest.mark.uat
@pytest.mark.slow
class TestEndToEndWorkflowFailures:
    """Test end-to-end workflow failure scenarios."""

    def test_workflow_fails_with_invalid_catalog(
        self, http_client: httpx.Client, auth_headers_with_ids: dict
    ):
        """Test workflow fails gracefully with invalid catalog."""
        invalid_catalog = b"{ invalid json"
        
        payload = {
            "client_id": "uat-e2e-failure-client",
            "client_name": "UAT E2E Failure Test",
        }
        
        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]
        
        files = {
            "file": ("catalog.json", invalid_catalog, "application/json")
        }
        
        parse_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/parse-catalog",
            files=files,
            headers={"Authorization": auth_headers_with_ids["Authorization"]}
        )
        
        assert parse_response.status_code in [400, 422]
        print("✓ Workflow correctly rejected invalid catalog")

    def test_workflow_cannot_skip_stages(
        self, http_client: httpx.Client, auth_headers_with_ids: dict, real_catalog_content: bytes
    ):
        """Test workflow enforces sequential stage execution."""
        payload = {
            "client_id": "uat-e2e-skip-client",
            "client_name": "UAT E2E Skip Test",
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
        
        time.sleep(10)
        
        repo_response = http_client.post(
            f"/api/v1/jobs/{job_id}/stages/create-local-repository",
            headers=auth_headers_with_ids
        )
        assert repo_response.status_code in [400, 409]
        print("✓ Cannot skip generate-input-files stage")
