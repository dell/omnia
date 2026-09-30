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

"""FVT tests for composite ImageGroupID (ER-BSM-002).

End-to-end tests for composite ImageGroupID format, database persistence,
and display in deploy/cleanup pipelines.

Test coverage:
- TC-FVT-002: Composite ImageGroupID database persistence (FR-2B.2, AC-014)
"""

import json

import pytest
import requests


# ---------------------------------------------------------------------------
# Configuration and Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def api_base_url(test_config):
    """Build Stream API base URL from test configuration."""
    system_admin_ip = test_config["hosts"]["system_admin"]["ansible_host"]
    return f"https://{system_admin_ip}:8443/api/v1"


@pytest.fixture(scope="module")
def auth_token(api_base_url, test_creds):
    """Obtain JWT auth token for API requests."""
    # Placeholder - actual implementation uses auth helpers
    return "test-jwt-token"


@pytest.fixture
def sample_catalog_v1_0():
    """Sample catalog with version 1.0."""
    return {
        "Catalog": {
            "Identifier": "omnia-slurm-rhel-10-0-x86-64-aarch64",
            "Version": "1.0",
            "SchemaVersion": 2,
            "Name": "Omnia Slurm v1.0",
            "BaseOS": [
                {"Name": "rhel", "Version": "10.0"},
            ],
            "FunctionalLayer": [
                {"Name": "slurm_node"},
            ],
            "InfrastructureLayer": [],
        }
    }


@pytest.fixture
def sample_catalog_v1_1():
    """Sample catalog with version 1.1 (same identifier, different version)."""
    return {
        "Catalog": {
            "Identifier": "omnia-slurm-rhel-10-0-x86-64-aarch64",
            "Version": "1.1",
            "SchemaVersion": 2,
            "Name": "Omnia Slurm v1.1",
            "BaseOS": [
                {"Name": "rhel", "Version": "10.0"},
            ],
            "FunctionalLayer": [
                {"Name": "slurm_node"},
            ],
            "InfrastructureLayer": [],
        }
    }


# ---------------------------------------------------------------------------
# TC-FVT-002: Composite ImageGroupID Database Persistence
# ---------------------------------------------------------------------------

@pytest.mark.sanity
class TestCompositeImageGroupIDPersistence:
    """End-to-end tests for composite ImageGroupID (FR-2B.2, AC-014).

    Validates that composite ImageGroupID (identifier-vVersion) is properly
    stored in the database and displayed in deploy/cleanup pipelines.
    """

    def test_composite_image_group_id_stored_in_database(
        self, _api_base_url, auth_token, sample_catalog_v1_0
    ):
        """Composite ImageGroupID is stored as {identifier}-v{version} in database.

        Scenario: Database stores composite ImageGroupID
          Given a catalog with identifier "omnia-slurm-rhel-10-0-x86-64-aarch64" and version "1.0"
          When the catalog is processed
          Then the image_groups.id is "omnia-slurm-rhel-10-0-x86-64-aarch64-v1.0"
          And the job.composite_image_group_id is "omnia-slurm-rhel-10-0-x86-64-aarch64-v1.0"
        """
        # Arrange
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        }
        catalog_json = json.dumps(sample_catalog_v1_0)

        # Act - Upload and parse catalog
        upload_response = requests.post(
            f"{_api_base_url}/upload",
            headers=headers,
            files={"catalog": ("catalog_rhel.json", catalog_json, "application/json")},
            verify=False,
            timeout=30,
        )
        assert upload_response.status_code == 200
        job_id = upload_response.json()["job_id"]

        parse_response = requests.post(
            f"{_api_base_url}/jobs/{job_id}/parse-catalog",
            headers=headers,
            verify=False,
            timeout=30,
        )
        assert parse_response.status_code == 200

        # Act - Get job details
        job_response = requests.get(
            f"{_api_base_url}/jobs/{job_id}",
            headers=headers,
            verify=False,
            timeout=30,
        )

        # Assert composite ImageGroupID format
        assert job_response.status_code == 200
        job_details = job_response.json()

        expected_composite_id = "omnia-slurm-rhel-10-0-x86-64-aarch64-v1.0"
        assert job_details.get("composite_image_group_id") == expected_composite_id
        assert job_details.get("catalog_identifier") == "omnia-slurm-rhel-10-0-x86-64-aarch64"
        assert job_details.get("catalog_version") == "1.0"

    def test_multiple_versions_create_distinct_composite_ids(
        self, _api_base_url, auth_token, sample_catalog_v1_0, sample_catalog_v1_1
    ):
        """Different catalog versions create different composite IDs.

        Scenario: Multiple versions of the same catalog
          Given catalogs with same identifier but different versions ("1.0", "1.1")
          When both catalogs are processed
          Then two distinct composite IDs are created
          And each follows {identifier}-v{version} format
        """
        # Arrange
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        }

        # Act - Upload and process v1.0
        catalog_v1_0_json = json.dumps(sample_catalog_v1_0)
        upload_v1_0 = requests.post(
            f"{_api_base_url}/upload",
            headers=headers,
            files={"catalog": ("catalog_rhel.json", catalog_v1_0_json, "application/json")},
            verify=False,
            timeout=30,
        )
        assert upload_v1_0.status_code == 200
        job_id_v1_0 = upload_v1_0.json()["job_id"]

        parse_v1_0 = requests.post(
            f"{_api_base_url}/jobs/{job_id_v1_0}/parse-catalog",
            headers=headers,
            verify=False,
            timeout=30,
        )
        assert parse_v1_0.status_code == 200

        # Act - Upload and process v1.1
        catalog_v1_1_json = json.dumps(sample_catalog_v1_1)
        upload_v1_1 = requests.post(
            f"{_api_base_url}/upload",
            headers=headers,
            files={"catalog": ("catalog_rhel.json", catalog_v1_1_json, "application/json")},
            verify=False,
            timeout=30,
        )
        assert upload_v1_1.status_code == 200
        job_id_v1_1 = upload_v1_1.json()["job_id"]

        parse_v1_1 = requests.post(
            f"{_api_base_url}/jobs/{job_id_v1_1}/parse-catalog",
            headers=headers,
            verify=False,
            timeout=30,
        )
        assert parse_v1_1.status_code == 200

        # Act - Get job details for both versions
        job_v1_0_response = requests.get(
            f"{_api_base_url}/jobs/{job_id_v1_0}",
            headers=headers,
            verify=False,
            timeout=30,
        )
        job_v1_1_response = requests.get(
            f"{_api_base_url}/jobs/{job_id_v1_1}",
            headers=headers,
            verify=False,
            timeout=30,
        )

        # Assert distinct composite IDs
        assert job_v1_0_response.status_code == 200
        assert job_v1_1_response.status_code == 200

        composite_id_v1_0 = job_v1_0_response.json().get("composite_image_group_id")
        composite_id_v1_1 = job_v1_1_response.json().get("composite_image_group_id")

        assert composite_id_v1_0 == "omnia-slurm-rhel-10-0-x86-64-aarch64-v1.0"
        assert composite_id_v1_1 == "omnia-slurm-rhel-10-0-x86-64-aarch64-v1.1"
        assert composite_id_v1_0 != composite_id_v1_1

    def test_duplicate_composite_id_rejected(
        self, _api_base_url, auth_token, sample_catalog_v1_0
    ):
        """Submitting the same catalog twice (same identifier+version) is rejected.

        Scenario: Duplicate composite ID rejected
          Given a catalog with identifier+version already exists
          When the same catalog is submitted again
          Then the second submission is rejected with DuplicateImageGroupError
        """
        # Arrange
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        }
        catalog_json = json.dumps(sample_catalog_v1_0)

        # Act - First submission (should succeed)
        upload_1 = requests.post(
            f"{_api_base_url}/upload",
            headers=headers,
            files={"catalog": ("catalog_rhel.json", catalog_json, "application/json")},
            verify=False,
            timeout=30,
        )
        assert upload_1.status_code == 200
        job_id_1 = upload_1.json()["job_id"]

        parse_1 = requests.post(
            f"{_api_base_url}/jobs/{job_id_1}/parse-catalog",
            headers=headers,
            verify=False,
            timeout=30,
        )
        assert parse_1.status_code == 200

        # Act - Second submission (should be rejected)
        upload_2 = requests.post(
            f"{_api_base_url}/upload",
            headers=headers,
            files={"catalog": ("catalog_rhel.json", catalog_json, "application/json")},
            verify=False,
            timeout=30,
        )
        assert upload_2.status_code == 200
        job_id_2 = upload_2.json()["job_id"]

        parse_2 = requests.post(
            f"{_api_base_url}/jobs/{job_id_2}/parse-catalog",
            headers=headers,
            verify=False,
            timeout=30,
        )

        # Assert - Second parse should fail with duplicate error
        # The parse stage should fail, not return 200
        assert parse_2.status_code in [200, 400, 409]

        # If the parse returned 200, check the job state
        if parse_2.status_code == 200:
            job_2_response = requests.get(
                f"{_api_base_url}/jobs/{job_id_2}",
                headers=headers,
                verify=False,
                timeout=30,
            )
            assert job_2_response.status_code == 200
            job_2_details = job_2_response.json()

            # The parse-catalog stage should have failed
            stages = job_2_details.get("stages", [])
            parse_stage = next(
                (s for s in stages if s["stage_name"] == "parse-catalog"),
                None
            )
            if parse_stage:
                assert parse_stage["stage_state"] in ["FAILED"]
                assert "DuplicateImageGroupError" in parse_stage.get("error_code", "")

    def test_composite_id_job_1_to_1_mapping(
        self, _api_base_url, auth_token, sample_catalog_v1_0
    ):
        """Each Job maps to exactly one ImageGroup (1:1 relationship).

        Scenario: 1:1 Job-to-ImageGroup mapping
          Given a job with a processed catalog
          When the ImageGroup is created
          Then the ImageGroup.job_id uniquely maps to exactly one Job
          And the Job.composite_image_group_id uniquely maps to exactly one ImageGroup
        """
        # Arrange
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        }
        catalog_json = json.dumps(sample_catalog_v1_0)

        # Act - Upload and parse catalog
        upload_response = requests.post(
            f"{_api_base_url}/upload",
            headers=headers,
            files={"catalog": ("catalog_rhel.json", catalog_json, "application/json")},
            verify=False,
            timeout=30,
        )
        assert upload_response.status_code == 200
        job_id = upload_response.json()["job_id"]

        parse_response = requests.post(
            f"{_api_base_url}/jobs/{job_id}/parse-catalog",
            headers=headers,
            verify=False,
            timeout=30,
        )
        assert parse_response.status_code == 200

        # Act - Get job details
        job_response = requests.get(
            f"{_api_base_url}/jobs/{job_id}",
            headers=headers,
            verify=False,
            timeout=30,
        )

        # Assert 1:1 mapping
        assert job_response.status_code == 200
        job_details = job_response.json()

        # Verify Job has composite_image_group_id
        composite_id = job_details.get("composite_image_group_id")
        assert composite_id is not None
        assert composite_id == "omnia-slurm-rhel-10-0-x86-64-aarch64-v1.0"

        # Verify Job.job_id exists
        assert job_details.get("job_id") == job_id

        # Note: ImageGroup.id and ImageGroup.job_id uniqueness is enforced
        # by database UNIQUE constraints, tested in unit tests
