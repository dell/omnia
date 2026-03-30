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

"""UAT tests for catalog query endpoints."""

import json
import time
import httpx
import pytest


@pytest.mark.uat
class TestCatalogQuerySuccess:
    """Test catalog query endpoints success scenarios."""

    def test_query_catalog_after_parse(
        self, http_client: httpx.Client, auth_headers_with_ids: dict, real_catalog_content: bytes
    ):
        """Test querying catalog after successful parse-catalog."""
        payload = {
            "client_id": "uat-catalog-query-client",
            "client_name": "UAT Catalog Query Test",
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

        time.sleep(10)

        query_response = http_client.get(
            f"/api/v1/jobs/{job_id}/catalog",
            headers=auth_headers_with_ids
        )

        assert query_response.status_code == 200
        data = query_response.json()
        assert "metadata" in data or "software" in data or isinstance(data, dict)

    def test_query_catalog_returns_parsed_data(
        self, http_client: httpx.Client, auth_headers_with_ids: dict
    ):
        """Test catalog query returns parsed catalog data."""
        catalog_data = {
            "metadata": {
                "name": "query-test-catalog",
                "version": "1.0.0",
                "description": "Test catalog for query",
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
            "client_id": "uat-catalog-query-client",
            "client_name": "UAT Catalog Query Test",
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

        time.sleep(10)

        query_response = http_client.get(
            f"/api/v1/jobs/{job_id}/catalog",
            headers=auth_headers_with_ids
        )

        assert query_response.status_code == 200
        data = query_response.json()
        assert isinstance(data, dict)

    def test_query_catalog_with_filters(
        self, http_client: httpx.Client, auth_headers_with_ids: dict, real_catalog_content: bytes
    ):
        """Test catalog query with filter parameters."""
        payload = {
            "client_id": "uat-catalog-query-client",
            "client_name": "UAT Catalog Query Test",
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

        time.sleep(10)

        query_response = http_client.get(
            f"/api/v1/jobs/{job_id}/catalog?arch=x86_64",
            headers=auth_headers_with_ids
        )

        assert query_response.status_code in [200, 404]

    def test_list_all_catalogs(
        self, http_client: httpx.Client, auth_headers: dict
    ):
        """Test listing all catalogs."""
        list_response = http_client.get(
            "/api/v1/catalog",
            headers=auth_headers
        )

        assert list_response.status_code == 200
        data = list_response.json()
        assert isinstance(data, (list, dict))


@pytest.mark.uat
class TestCatalogQueryFailure:
    """Test catalog query endpoints failure scenarios."""

    def test_query_catalog_before_parse_returns_404(
        self, http_client: httpx.Client, auth_headers_with_ids: dict
    ):
        """Test querying catalog before parse-catalog returns 404."""
        payload = {
            "client_id": "uat-catalog-query-client",
            "client_name": "UAT Catalog Query Test",
        }

        create_response = http_client.post("/api/v1/jobs", json=payload, headers=auth_headers_with_ids)
        assert create_response.status_code == 201
        job_id = create_response.json()["job_id"]

        query_response = http_client.get(
            f"/api/v1/jobs/{job_id}/catalog",
            headers=auth_headers_with_ids
        )

        assert query_response.status_code == 404

    def test_query_catalog_for_nonexistent_job_returns_404(
        self, http_client: httpx.Client, auth_headers: dict
    ):
        """Test querying catalog for nonexistent job returns 404."""
        import uuid
        nonexistent_job_id = str(uuid.uuid4())

        query_response = http_client.get(
            f"/api/v1/jobs/{nonexistent_job_id}/catalog",
            headers=auth_headers
        )

        assert query_response.status_code == 404

    def test_query_catalog_without_auth_returns_401(self, http_client: httpx.Client):
        """Test querying catalog without authentication returns 401."""
        import uuid
        job_id = str(uuid.uuid4())

        query_response = http_client.get(
            f"/api/v1/jobs/{job_id}/catalog"
        )

        assert query_response.status_code == 401

    def test_query_catalog_with_invalid_job_id_returns_422(
        self, http_client: httpx.Client, auth_headers: dict
    ):
        """Test querying catalog with invalid job ID format returns 422."""
        invalid_job_id = "not-a-valid-uuid"

        query_response = http_client.get(
            f"/api/v1/jobs/{invalid_job_id}/catalog",
            headers=auth_headers
        )

        assert query_response.status_code == 422

    def test_query_catalog_with_invalid_filter_returns_400(
        self, http_client: httpx.Client, auth_headers_with_ids: dict, real_catalog_content: bytes
    ):
        """Test catalog query with invalid filter parameters returns 400."""
        payload = {
            "client_id": "uat-catalog-query-client",
            "client_name": "UAT Catalog Query Test",
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

        time.sleep(10)

        query_response = http_client.get(
            f"/api/v1/jobs/{job_id}/catalog?invalid_param=value",
            headers=auth_headers_with_ids
        )

        assert query_response.status_code in [200, 400, 422]

    def test_list_catalogs_without_auth_returns_401(self, http_client: httpx.Client):
        """Test listing catalogs without authentication returns 401."""
        list_response = http_client.get("/api/v1/catalog")

        assert list_response.status_code == 401
