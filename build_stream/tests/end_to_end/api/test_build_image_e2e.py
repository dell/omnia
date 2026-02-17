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

"""End-to-end tests for Build Image API."""

import json
import subprocess
import time
from pathlib import Path
from typing import Dict, Any

import pytest
import requests


class TestBuildImageE2E:
    """End-to-end tests for build image workflow."""

    BASE_URL = "http://localhost:8000"
    API_PREFIX = "/api/v1"
    AUTH_TOKEN = "test-e2e-token"
    REQUEST_TIMEOUT = 30

    @classmethod
    def setup_class(cls):
        """Setup class with server startup."""
        # Start the API server in background
        cls.server_process = subprocess.Popen(
            ["python", "main.py"],
            cwd="/opt/omnia/omnia/omnia_code/build_stream",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # Wait for server to start
        time.sleep(5)

        # Verify server is running
        try:
            response = requests.get(
                f"{cls.BASE_URL}/health",
                timeout=cls.REQUEST_TIMEOUT,
            )
            assert response.status_code == 200
        except requests.exceptions.ConnectionError:
            pytest.skip("API server not available")

    @classmethod
    def teardown_class(cls):
        """Cleanup by stopping server."""
        if hasattr(cls, 'server_process'):
            cls.server_process.terminate()
            cls.server_process.wait()

    def get_headers(self, correlation_id: str = None) -> Dict[str, str]:
        """Get request headers."""
        headers = {
            "Authorization": f"Bearer {self.AUTH_TOKEN}",
            "Content-Type": "application/json",
        }
        if correlation_id:
            headers["X-Correlation-Id"] = correlation_id
        return headers

    def test_full_build_image_workflow_x86_64(self):
        """Test complete build image workflow for x86_64."""
        correlation_id = "e2e-test-x86_64"
        headers = self.get_headers(correlation_id)

        # Step 1: Create a job
        create_job_response = requests.post(
            f"{self.BASE_URL}{self.API_PREFIX}/jobs",
            json={
                "stage": "build-image",
                "input_parameters": {
                    "architecture": "x86_64",
                    "image_key": "e2e-test-image",
                    "functional_groups": [
                        "slurm_control_node_x86_64",
                        "slurm_node_x86_64",
                        "login_node_x86_64"
                    ]
                }
            },
            headers=headers,
            timeout=self.REQUEST_TIMEOUT,
        )
        assert create_job_response.status_code == 201
        job_data = create_job_response.json()
        job_id = job_data["job_id"]
        assert job_id

        # Step 2: Verify job was created with build-image stage
        get_job_response = requests.get(
            f"{self.BASE_URL}{self.API_PREFIX}/jobs/{job_id}",
            headers=headers,
            timeout=self.REQUEST_TIMEOUT,
        )
        assert get_job_response.status_code == 200
        job_detail = get_job_response.json()
        stages = {stage["stage_name"]: stage for stage in job_detail["stages"]}
        assert "build-image" in stages
        assert stages["build-image"]["status"] == "PENDING"

        # Step 3: Trigger build image stage
        build_image_response = requests.post(
            f"{self.BASE_URL}{self.API_PREFIX}/jobs/{job_id}/stages/build-image",
            json={
                "architecture": "x86_64",
                "image_key": "e2e-test-image",
                "functional_groups": [
                    "slurm_control_node_x86_64",
                    "slurm_node_x86_64",
                    "login_node_x86_64"
                ]
            },
            headers=headers
        )
        assert build_image_response.status_code == 202
        build_data = build_image_response.json()
        assert build_data["job_id"] == job_id
        assert build_data["stage"] == "build-image"
        assert build_data["status"] == "accepted"
        assert build_data["architecture"] == "x86_64"
        assert build_data["image_key"] == "e2e-test-image"
        assert len(build_data["functional_groups"]) == 3

        # Step 4: Verify stage is now STARTED
        get_job_response2 = requests.get(
            f"{self.BASE_URL}{self.API_PREFIX}/jobs/{job_id}",
            headers=headers,
            timeout=self.REQUEST_TIMEOUT,
        )
        assert get_job_response2.status_code == 200
        job_detail2 = get_job_response2.json()
        stages2 = {stage["stage_name"]: stage for stage in job_detail2["stages"]}
        assert stages2["build-image"]["status"] == "STARTED"

        # Step 5: Verify request file in queue
        queue_dir = Path("/opt/omnia/build_stream/queue/requests")
        request_files = list(queue_dir.glob(f"{job_id}_build-image_*.json"))
        assert len(request_files) == 1

        # Verify request file content
        request_data = json.loads(request_files[0].read_text())
        assert request_data["job_id"] == job_id
        assert request_data["architecture"] == "x86_64"
        assert request_data["image_key"] == "e2e-test-image"
        assert request_data["functional_groups"] == [
            "slurm_control_node_x86_64",
            "slurm_node_x86_64",
            "login_node_x86_64"
        ]
        assert request_data["playbook_path"] == "/omnia/build_image_x86_64/build_image_x86_64.yml"
        assert request_data["correlation_id"] == correlation_id

        # Step 6: Verify playbook command generation
        with open(request_files[0], "r", encoding="utf-8") as f:
            request_content = json.load(f)
        
        # The request should contain all necessary fields for playbook execution
        assert "request_id" in request_content
        assert "timeout_minutes" in request_content
        assert "submitted_at" in request_content
        assert "inventory_file_path" not in request_content  # Not needed for x86_64
        
        # Step 7: Verify stage naming (should be build-image-x86_64)
        assert request_content["stage_name"] == "build-image-x86_64"

    def test_full_build_image_workflow_aarch64(self):
        """Test complete build image workflow for aarch64."""
        correlation_id = "e2e-test-aarch64"
        headers = self.get_headers(correlation_id)

        # Step 1: Create a job
        create_job_response = requests.post(
            f"{self.BASE_URL}{self.API_PREFIX}/jobs",
            json={
                "stage": "build-image",
                "input_parameters": {
                    "architecture": "aarch64",
                    "image_key": "e2e-test-image-arm",
                    "functional_groups": [
                        "slurm_control_node_aarch64",
                        "slurm_node_aarch64"
                    ]
                }
            },
            headers=headers
        )
        assert create_job_response.status_code == 201
        job_data = create_job_response.json()
        job_id = job_data["job_id"]

        # Step 2: Create build_stream_config.yml with inventory host
        # Use the consolidated repository path structure
        input_dir = Path("/opt/omnia/input/project_default")
        input_dir.mkdir(parents=True, exist_ok=True)
        
        # Create default.yml for project name resolution
        default_file = Path("/opt/omnia/input/default.yml")
        default_file.write_text("project_name: project_default\n", encoding="utf-8")
        
        config_file = input_dir / "build_stream_config.yml"
        config_file.write_text("aarch64_inventory_host: 10.3.0.170\n", encoding="utf-8")

        # Step 3: Trigger build image stage
        build_image_response = requests.post(
            f"{self.BASE_URL}{self.API_PREFIX}/jobs/{job_id}/stages/build-image",
            json={
                "architecture": "aarch64",
                "image_key": "e2e-test-image-arm",
                "functional_groups": [
                    "slurm_control_node_aarch64",
                    "slurm_node_aarch64"
                ]
            },
            headers=headers
        )
        assert build_image_response.status_code == 202
        build_data = build_image_response.json()
        assert build_data["architecture"] == "aarch64"

        # Step 4: Verify request file and inventory file creation
        queue_dir = Path("/opt/omnia/build_stream/queue/requests")
        request_files = list(queue_dir.glob(f"{job_id}_build-image_*.json"))
        assert len(request_files) == 1

        request_data = json.loads(request_files[0].read_text(encoding="utf-8"))
        assert request_data["playbook_path"] == "build_image_aarch64.yml"  # Only filename, not full path
        
        # Step 5: Verify inventory file was created by consolidated repository
        inventory_dir = Path("/opt/omnia/build_stream_inv")
        inventory_file = inventory_dir / job_id / "inv"
        assert inventory_file.exists(), "Inventory file should be created"
        
        # Verify inventory file content
        with open(inventory_file, 'r') as f:
            inventory_content = f.read()
        assert "10.3.0.170" in inventory_content, f"Inventory file should contain host IP: {inventory_content}"
        assert "[build_hosts]" in inventory_content, f"Inventory file should have proper format: {inventory_content}"
        
        # Step 6: Verify stage naming (should be build-image-aarch64)
        with open(request_files[0], "r", encoding="utf-8") as f:
            request_content = json.load(f)
        assert request_content["stage_name"] == "build-image-aarch64"
        
        # Step 7: Verify inventory_file_path is included in request
        assert "inventory_file_path" in request_content
        assert request_content["inventory_file_path"] == str(inventory_file)

    def test_consolidated_repository_functionality(self):
        """Test consolidated NfsInputRepository functionality."""
        correlation_id = "e2e-test-consolidated-repo"
        headers = self.get_headers(correlation_id)

        # Step 1: Create a job
        create_job_response = requests.post(
            f"{self.BASE_URL}{self.API_PREFIX}/jobs",
            json={
                "stage": "build-image",
                "input_parameters": {
                    "architecture": "aarch64",
                    "image_key": "e2e-consolidated-test",
                    "functional_groups": ["slurm_control_node_aarch64"]
                }
            },
            headers=headers
        )
        assert create_job_response.status_code == 201
        job_data = create_job_response.json()
        job_id = job_data["job_id"]

        # Step 2: Setup consolidated repository paths
        input_dir = Path("/opt/omnia/input")
        input_dir.mkdir(parents=True, exist_ok=True)
        
        # Create default.yml for project name resolution
        default_file = input_dir / "default.yml"
        default_file.write_text("project_name: project_default\n", encoding="utf-8")
        
        # Create config with correct key name
        config_file = input_dir / "project_default" / "build_stream_config.yml"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("aarch64_inventory_host: 192.168.1.200\n", encoding="utf-8")

        # Step 3: Trigger build image stage
        build_image_response = requests.post(
            f"{self.BASE_URL}{self.API_PREFIX}/jobs/{job_id}/stages/build-image",
            json={
                "architecture": "aarch64",
                "image_key": "e2e-consolidated-test",
                "functional_groups": ["slurm_control_node_aarch64"]
            },
            headers=headers
        )
        assert build_image_response.status_code == 202

        # Step 4: Verify consolidated repository functionality
        # 4a: Verify config reading works
        queue_dir = Path("/opt/omnia/build_stream/queue/requests")
        request_files = list(queue_dir.glob(f"{job_id}_build-image_*.json"))
        assert len(request_files) == 1
        
        # 4b: Verify inventory file creation
        inventory_dir = Path("/opt/omnia/build_stream_inv")
        inventory_file = inventory_dir / job_id / "inv"
        assert inventory_file.exists(), "Consolidated repository should create inventory file"
        
        # 4c: Verify inventory file content
        with open(inventory_file, 'r') as f:
            content = f.read()
        assert "192.168.1.200" in content
        assert "[build_hosts]" in content
        
        # 4d: Verify input directory paths work
        build_stream_dir = Path("/opt/omnia/build_stream")
        source_path = build_stream_dir / job_id / "input"
        dest_path = input_dir / "project_default"
        
        # These paths should be accessible through the consolidated repository
        assert dest_path.exists(), "Destination input directory should exist"
        
        # 4e: Verify request contains correct playbook filename (not full path)
        with open(request_files[0], "r", encoding="utf-8") as f:
            request_content = json.load(f)
        assert request_content["playbook_path"] == "build_image_aarch64.yml"
        assert request_content["stage_name"] == "build-image-aarch64"
        assert "inventory_file_path" in request_content

    def test_build_image_error_cases(self):
        """Test various error scenarios."""
        correlation_id = "e2e-test-errors"
        headers = self.get_headers(correlation_id)

        # Test 1: Invalid architecture
        create_job_response = requests.post(
            f"{self.BASE_URL}{self.API_PREFIX}/jobs",
            json={
                "stage": "build-image",
                "input_parameters": {
                    "architecture": "x86_64",
                    "image_key": "test-image",
                    "functional_groups": ["group1"]
                }
            },
            headers=headers
        )
        job_id = create_job_response.json()["job_id"]

        error_response = requests.post(
            f"{self.BASE_URL}{self.API_PREFIX}/jobs/{job_id}/stages/build-image",
            json={
                "architecture": "invalid_arch",
                "image_key": "test-image",
                "functional_groups": ["group1"]
            },
            headers=headers
        )
        assert error_response.status_code == 400
        assert error_response.json()["error"] == "INVALID_ARCHITECTURE"

        # Test 2: Missing inventory host for aarch64
        create_job_response2 = requests.post(
            f"{self.BASE_URL}{self.API_PREFIX}/jobs",
            json={
                "stage": "build-image",
                "input_parameters": {
                    "architecture": "aarch64",
                    "image_key": "test-image",
                    "functional_groups": ["group1"]
                }
            },
            headers=headers
        )
        job_id2 = create_job_response2.json()["job_id"]

        # Don't create config file (no inventory host)
        error_response2 = requests.post(
            f"{self.BASE_URL}{self.API_PREFIX}/jobs/{job_id2}/stages/build-image",
            json={
                "architecture": "aarch64",
                "image_key": "test-image",
                "functional_groups": ["group1"]
            },
            headers=headers
        )
        assert error_response2.status_code == 400
        assert error_response2.json()["error"] == "INVENTORY_HOST_MISSING"

    def test_build_image_concurrent_requests(self):
        """Test handling concurrent build image requests."""
        correlation_id = "e2e-test-concurrent"
        headers = self.get_headers(correlation_id)

        # Create multiple jobs
        job_ids = []
        for i in range(3):
            response = requests.post(
                f"{self.BASE_URL}{self.API_PREFIX}/jobs",
                json={
                    "stage": "build-image",
                    "input_parameters": {
                        "architecture": "x86_64",
                        "image_key": f"concurrent-image-{i}",
                        "functional_groups": [f"group{i}"]
                    }
                },
                headers=headers,
                timeout=self.REQUEST_TIMEOUT,
            )
            job_ids.append(response.json()["job_id"])

        # Submit build image requests concurrently
        import concurrent.futures

        def submit_build_image(job_id):
            return requests.post(
                f"{self.BASE_URL}{self.API_PREFIX}/jobs/{job_id}/stages/build-image",
                json={
                    "architecture": "x86_64",
                    "image_key": f"concurrent-image-{job_id}",
                    "functional_groups": [f"group{job_id}"]
                },
                headers=headers
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(submit_build_image, job_id) for job_id in job_ids]
            responses = [future.result() for future in futures]

        # All requests should succeed
        for response in responses:
            assert response.status_code == 202

        # Verify all requests are in queue
        queue_dir = Path("/opt/omnia/build_stream/queue/requests")
        request_files = list(queue_dir.glob("*_build-image_*.json"))
        assert len(request_files) >= 3  # At least our 3 requests

    def test_build_image_audit_trail(self):
        """Test that build image operations create audit events."""
        correlation_id = "e2e-test-audit"
        headers = self.get_headers(correlation_id)

        # Create job and trigger build image
        create_job_response = requests.post(
            f"{self.BASE_URL}{self.API_PREFIX}/jobs",
            json={
                "stage": "build-image",
                "input_parameters": {
                    "architecture": "x86_64",
                    "image_key": "audit-test-image",
                    "functional_groups": ["group1"]
                }
            },
            headers=headers
        )
        job_id = create_job_response.json()["job_id"]

        build_image_response = requests.post(
            f"{self.BASE_URL}{self.API_PREFIX}/jobs/{job_id}/stages/build-image",
            json={
                "architecture": "x86_64",
                "image_key": "audit-test-image",
                "functional_groups": ["group1"]
            },
            headers=headers
        )
        assert build_image_response.status_code == 202

        # Check audit events
        audit_response = requests.get(
            f"{self.BASE_URL}{self.API_PREFIX}/jobs/{job_id}/audit",
            headers=headers,
            timeout=self.REQUEST_TIMEOUT,
        )
        assert audit_response.status_code == 200
        audit_events = audit_response.json()

        # Should have STAGE_STARTED event for build-image
        build_image_events = [
            event for event in audit_events
            if event["event_type"] == "STAGE_STARTED" and 
               event["details"]["stage_name"] == "build-image"
        ]
        assert len(build_image_events) == 1
        assert build_image_events[0]["details"]["architecture"] == "x86_64"
        assert build_image_events[0]["details"]["image_key"] == "audit-test-image"
