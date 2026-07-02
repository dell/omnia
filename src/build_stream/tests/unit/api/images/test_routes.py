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

"""Unit tests for Images API routes."""

import uuid

import pytest
from fastapi import HTTPException

from api.images.routes import list_images
from api.images.schemas import ListImagesResponse, PaginationResponse, ImageGroupResponse
from core.image_group.value_objects import ImageGroupStatus


def _uuid():
    return str(uuid.uuid4())


class MockListImagesUseCase:
    """Mock use case for testing."""

    def __init__(self, result=None, error=None):
        self._result = result
        self._error = error
        self.calls = []

    def execute(self, status, limit, offset):
        self.calls.append({"status": status, "limit": limit, "offset": offset})
        if self._error:
            raise self._error
        return self._result or ListImagesResponse(
            image_groups=[],
            pagination=PaginationResponse(
                total_count=0, limit=limit, offset=offset, has_more=False
            ),
        )


class TestListImagesRoute:
    """Tests for GET /api/v1/images route handler."""

    def test_success_default_params(self):
        """Returns 200 with default query parameters."""
        use_case = MockListImagesUseCase()
        result = list_images(
            status_filter="BUILT",
            limit=100,
            offset=0,
            token_data={"client_id": "test-client", "scopes": ["catalog:read"]},
            _={"client_id": "test-client", "scopes": ["catalog:read"]},
            use_case=use_case,
        )
        assert isinstance(result, ListImagesResponse)
        assert len(use_case.calls) == 1
        # status_filter="BUILT" now triggers cumulative query (status=None for all post-BUILT states)
        assert use_case.calls[0]["status"] is None

    def test_invalid_status_returns_400(self):
        """Returns 400 for invalid status filter."""
        use_case = MockListImagesUseCase()
        with pytest.raises(HTTPException) as exc_info:
            list_images(
                status_filter="INVALID_STATUS",
                limit=100,
                offset=0,
                token_data={"client_id": "test-client", "scopes": ["catalog:read"]},
                _={"client_id": "test-client", "scopes": ["catalog:read"]},
                use_case=use_case,
            )
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["error_code"] == "INVALID_STATUS"

    def test_passes_status_to_use_case(self):
        """Passes parsed status enum to use case."""
        use_case = MockListImagesUseCase()
        list_images(
            status_filter="DEPLOYED",
            limit=50,
            offset=10,
            token_data={"client_id": "test-client", "scopes": ["catalog:read"]},
            _={"client_id": "test-client", "scopes": ["catalog:read"]},
            use_case=use_case,
        )
        assert use_case.calls[0]["status"] == ImageGroupStatus.DEPLOYED
        assert use_case.calls[0]["limit"] == 50
        assert use_case.calls[0]["offset"] == 10

    def test_internal_error_returns_500(self):
        """Returns 500 when use case raises unexpected exception."""
        use_case = MockListImagesUseCase(error=RuntimeError("DB connection lost"))
        with pytest.raises(HTTPException) as exc_info:
            list_images(
                status_filter="BUILT",
                limit=100,
                offset=0,
                token_data={"client_id": "test-client", "scopes": ["catalog:read"]},
                _={"client_id": "test-client", "scopes": ["catalog:read"]},
                use_case=use_case,
            )
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail["error_code"] == "INTERNAL_ERROR"

    def test_returns_populated_response(self):
        """Returns properly structured response with data."""
        from datetime import datetime, timezone
        expected = ListImagesResponse(
            image_groups=[
                ImageGroupResponse(
                    job_id=_uuid(),
                    image_group_id="cluster-v1",
                    images=[],
                    status="BUILT",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
            ],
            pagination=PaginationResponse(
                total_count=1, limit=100, offset=0, has_more=False
            ),
        )
        use_case = MockListImagesUseCase(result=expected)
        result = list_images(
            status_filter="BUILT",
            limit=100,
            offset=0,
            token_data={"client_id": "test-client", "scopes": ["catalog:read"]},
            _={"client_id": "test-client", "scopes": ["catalog:read"]},
            use_case=use_case,
        )
        assert len(result.image_groups) == 1
        assert result.image_groups[0].image_group_id == "cluster-v1"
