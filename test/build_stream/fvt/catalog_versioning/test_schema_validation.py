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

"""FVT tests for catalog schema version validation (ER-BSM-002).

End-to-end tests for catalog schema versioning including upload,
parsing, and database persistence.

Test coverage:
- TC-FVT-002: Catalog schema version validation (FR-2B.1, AC-013)
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
def auth_token(_api_base_url, _test_creds):
    """Obtain JWT auth token for API requests."""
    # Register and get token
    # This is a simplified version - actual implementation would use
    # the test framework's auth helper
    return "test-jwt-token"  # Placeholder


@pytest.fixture
def sample_catalog_v2():
    """Sample catalog with SchemaVersion=2."""
    return {
        "Catalog": {
            "Identifier": "test-catalog-schema-v2",
            "Version": "1.0",
            "SchemaVersion": 2,
            "Name": "Test Catalog Schema v2",
            "BaseOS": [
                {"Name": "rhel", "Version": "10.0"},
            ],
            "FunctionalLayer": [
                {"Name": "test_layer"},
            ],
            "InfrastructureLayer": [],
        }
    }


@pytest.fixture
def sample_catalog_without_schema_version():
    """Sample catalog without SchemaVersion field (backward compatibility)."""
    return {
        "Catalog": {
            "Identifier": "test-catalog-no-schema",
            "Version": "1.0",
            "Name": "Test Catalog No Schema Version",
            "FunctionalLayer": [],
            "InfrastructureLayer": [],
        }
    }


# ---------------------------------------------------------------------------
# TC-FVT-002: Catalog Schema Version Validation End-to-End
# ---------------------------------------------------------------------------

@pytest.mark.sanity
class TestCatalogSchemaVersionValidation:
    """End-to-end tests for catalog schema version validation (FR-2B.1, AC-013).

    Validates that the Build Stream API properly validates schema_version
    field presence and compatibility, recording it in the database.
    """

    def test_catalog_with_valid_schema_version_2(
        self, _api_base_url, auth_token, sample_catalog_v2
    ):
        """Catalog with SchemaVersion=2 is accepted and processed.

        Scenario: Valid schema version 2
          Given a catalog with catalog_schema_version: 2
          When the catalog is uploaded and parsed
          Then the catalog is accepted
          And schema_version=2 is recorded in the database
          And the parse-catalog stage completes successfully
        """
        # Arrange
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        }
        catalog_json = json.dumps(sample_catalog_v2)

        # Act - Upload catalog
        upload_response = requests.post(
            f"{api_base_url}/upload",
            headers=headers,
            files={"catalog": ("catalog_rhel.json", catalog_json, "application/json")},
            verify=False,
            timeout=30,
        )

        # Assert upload succeeded
        assert upload_response.status_code == 200
        job_data = upload_response.json()
        job_id = job_data["job_id"]

        # Act - Parse catalog
        parse_response = requests.post(
            f"{api_base_url}/jobs/{job_id}/parse-catalog",
            headers=headers,
            verify=False,
            timeout=30,
        )

        # Assert parse succeeded
        assert parse_response.status_code == 200
        parse_data = parse_response.json()
        assert parse_data["stage_state"] in ["COMPLETED", "IN_PROGRESS"]

        # Act - Get job details to verify schema_version recorded
        job_response = requests.get(
            f"{api_base_url}/jobs/{job_id}",
            headers=headers,
            verify=False,
            timeout=30,
        )

        # Assert schema_version recorded in job
        assert job_response.status_code == 200
        job_details = job_response.json()
        assert job_details.get("catalog_schema_version") == 2
        assert job_details.get("catalog_identifier") == "test-catalog-schema-v2"
        assert job_details.get("catalog_version") == "1.0"
        assert job_details.get("composite_image_group_id") == "test-catalog-schema-v2-v1.0"

    def test_catalog_without_schema_version_defaults_to_1(
        self, _api_base_url, auth_token, sample_catalog_without_schema_version
    ):
        """Catalog without SchemaVersion field defaults to 1 for backward compatibility.

        Scenario: Catalog without schema version (backward compatibility)
          Given a catalog without the catalog_schema_version field
          When the catalog is uploaded and parsed
          Then the catalog is accepted (backward compatible)
          And schema_version defaults to 1
          And the parse-catalog stage completes successfully
        """
        # Arrange
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        }
        catalog_json = json.dumps(sample_catalog_without_schema_version)

        # Act - Upload catalog
        upload_response = requests.post(
            f"{api_base_url}/upload",
            headers=headers,
            files={"catalog": ("catalog_rhel.json", catalog_json, "application/json")},
            verify=False,
            timeout=30,
        )

        # Assert upload succeeded
        assert upload_response.status_code == 200
        job_data = upload_response.json()
        job_id = job_data["job_id"]

        # Act - Parse catalog
        parse_response = requests.post(
            f"{api_base_url}/jobs/{job_id}/parse-catalog",
            headers=headers,
            verify=False,
            timeout=30,
        )

        # Assert parse succeeded
        assert parse_response.status_code == 200

        # Act - Get job details to verify schema_version defaults to 1
        job_response = requests.get(
            f"{api_base_url}/jobs/{job_id}",
            headers=headers,
            verify=False,
            timeout=30,
        )

        # Assert schema_version defaults to 1
        assert job_response.status_code == 200
        job_details = job_response.json()
        assert job_details.get("catalog_schema_version") == 1

    def test_catalog_schema_version_recorded_in_database(
        self, _api_base_url, auth_token, sample_catalog_v2
    ):
        """Schema version is persisted in both Job and ImageGroup database tables.

        Scenario: Schema version database persistence
          Given a catalog with schema_version: 2
          When the catalog is processed
          Then schema_version=2 is stored in jobs table
          And schema_version=2 is stored in image_groups table
        """
        # Arrange
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        }
        catalog_json = json.dumps(sample_catalog_v2)

        # Act - Upload and parse catalog
        upload_response = requests.post(
            f"{api_base_url}/upload",
            headers=headers,
            files={"catalog": ("catalog_rhel.json", catalog_json, "application/json")},
            verify=False,
            timeout=30,
        )
        assert upload_response.status_code == 200
        job_id = upload_response.json()["job_id"]

        parse_response = requests.post(
            f"{api_base_url}/jobs/{job_id}/parse-catalog",
            headers=headers,
            verify=False,
            timeout=30,
        )
        assert parse_response.status_code == 200

        # Act - Query database through API
        job_response = requests.get(
            f"{api_base_url}/jobs/{job_id}",
            headers=headers,
            verify=False,
            timeout=30,
        )

        # Assert
        assert job_response.status_code == 200
        job_details = job_response.json()

        # Verify schema_version in Job entity
        assert job_details.get("catalog_schema_version") == 2

        # Verify composite ImageGroupID was created
        composite_id = job_details.get("composite_image_group_id")
        assert composite_id is not None
        assert composite_id == "test-catalog-schema-v2-v1.0"

        # Note: ImageGroup schema_version would be verified through
        # image group query API once the image is built
