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

"""Unit tests for local repository API dependencies."""

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials

from api.local_repo.dependencies import (
    get_local_repo_correlation_id,
    get_create_local_repo_use_case,
    get_local_repo_client_id,
)
from core.jobs.value_objects import CorrelationId


class TestGetCorrelationId:
    """Tests for get_local_repo_correlation_id dependency."""

    def test_get_correlation_id_from_header(self):
        """Test getting correlation ID from X-Correlation-Id header."""
        correlation_id = str(uuid.uuid4())

        result = get_local_repo_correlation_id(correlation_id)

        assert isinstance(result, CorrelationId)
        assert str(result) == correlation_id

    def test_get_correlation_id_generates_new_id(self):
        """Test that new correlation ID is generated when not provided."""
        result = get_local_repo_correlation_id(None)

        assert isinstance(result, CorrelationId)
        assert str(result) is not None
        assert len(str(result)) > 0

    def test_get_correlation_id_empty_string(self):
        """Test that empty string generates new correlation ID."""
        result = get_local_repo_correlation_id("")

        assert isinstance(result, CorrelationId)
        assert str(result) is not None
        assert str(result) != ""

    def test_get_correlation_id_whitespace_only(self):
        """Test that whitespace-only string generates new correlation ID."""
        result = get_local_repo_correlation_id("   ")

        assert isinstance(result, CorrelationId)
        assert str(result) is not None
        assert str(result) != "   "


class TestGetCreateLocalRepoUseCase:
    """Tests for get_create_local_repo_use_case dependency."""

    def test_returns_use_case_instance(self):
        """Test that dependency returns use case instance."""
        use_case = get_create_local_repo_use_case()

        assert use_case is not None
        assert hasattr(use_case, 'execute')
        assert callable(use_case.execute)

    def test_use_case_is_factory(self):
        """Test that use case is created from factory (not singleton)."""
        use_case1 = get_create_local_repo_use_case()
        use_case2 = get_create_local_repo_use_case()

        # Factory creates new instances
        assert use_case1 is not use_case2
        assert type(use_case1) == type(use_case2)


class TestAuthenticationDependencies:
    """Tests for authentication dependencies."""

    def test_bearer_token_validation(self):
        """Test Bearer token validation."""
        # The dependency should extract ClientId from bearer token
        client_id = get_local_repo_client_id("Bearer test-token-123")
        assert str(client_id) == "test-token-123"

    def test_invalid_scheme_raises_exception(self):
        """Test that invalid scheme raises HTTPException."""
        # Should raise HTTPException for non-bearer scheme
        with pytest.raises(HTTPException) as exc_info:
            get_local_repo_client_id("Basic dGVzdDoxMjM=")

        assert exc_info.value.status_code == 401
        assert "Invalid authorization header format" in str(exc_info.value.detail)

    def test_missing_token_raises_exception(self):
        """Test that missing token raises HTTPException."""
        # Should raise HTTPException for empty token
        with pytest.raises(HTTPException) as exc_info:
            get_local_repo_client_id("Bearer ")

        assert exc_info.value.status_code == 401
        assert "Missing authentication token" in str(exc_info.value.detail)

    def test_long_token_truncated(self):
        """Test that long tokens are truncated to 128 chars."""
        long_token = "x" * 200
        client_id = get_local_repo_client_id(f"Bearer {long_token}")
        assert len(str(client_id)) == 128

