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

"""Unit tests for JWT auth dependencies and scope enforcement (ER-BSM-002).

Tests JWT authentication dependencies including admin scope enforcement
and authorization failure handling.

Test coverage:
- TC-UT-007: JWT admin scope enforcement (FR-5, AC-009)
"""

import pytest
from fastapi import HTTPException

from api.dependencies import (
    require_admin,
    require_admin_or_catalog_write,
    require_admin_or_job_write,
    require_any_scope,
    require_scope,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def token_with_admin_scope():
    """Token data with admin scope."""
    return {
        "client_id": "test-client-123",
        "scopes": ["admin"],
        "exp": 1234567890,
    }


@pytest.fixture
def token_with_job_write_scope():
    """Token data with job:write scope."""
    return {
        "client_id": "test-client-456",
        "scopes": ["job:write"],
        "exp": 1234567890,
    }


@pytest.fixture
def token_with_catalog_write_scope():
    """Token data with catalog:write scope."""
    return {
        "client_id": "test-client-789",
        "scopes": ["catalog:write"],
        "exp": 1234567890,
    }


@pytest.fixture
def token_without_admin_scope():
    """Token data without admin scope."""
    return {
        "client_id": "test-client-no-admin",
        "scopes": ["job:read", "catalog:read"],
        "exp": 1234567890,
    }


@pytest.fixture
def token_with_no_scopes():
    """Token data with empty scopes list."""
    return {
        "client_id": "test-client-empty",
        "scopes": [],
        "exp": 1234567890,
    }


# ---------------------------------------------------------------------------
# TC-UT-007: JWT Admin Scope Enforcement
# ---------------------------------------------------------------------------

class TestRequireAdminScope:
    """Test cases for admin scope enforcement (FR-5, AC-009).
    
    Validates that require_admin dependency properly enforces admin scope
    and raises 403 Forbidden for tokens without admin scope.
    """

    def test_require_admin_scope_success(self, token_with_admin_scope):
        """Token with admin scope passes admin requirement.
        
        Scenario: Config operation with admin scope succeeds
          Given the user has a valid JWT with "admin" scope
          When the require_admin dependency is invoked
          Then the request is authorized
          And the token data is returned
        """
        # Arrange
        dependency = require_admin

        # Act
        result = dependency(token_with_admin_scope)

        # Assert
        assert result == token_with_admin_scope
        assert "admin" in result["scopes"]

    def test_require_admin_scope_missing(self, token_without_admin_scope):
        """Token without admin scope raises 403 Forbidden.
        
        Scenario: Config operation without admin scope fails
          Given the user has a valid JWT without "admin" scope
          When the require_admin dependency is invoked
          Then the request is rejected with 403 Forbidden
          And an error message indicates missing admin scope
        """
        # Arrange
        dependency = require_admin

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            dependency(token_without_admin_scope)

        # Verify 403 Forbidden
        assert exc_info.value.status_code == 403
        assert "admin" in str(exc_info.value.detail).lower()

    def test_require_admin_scope_empty_scopes(self, token_with_no_scopes):
        """Token with no scopes raises 403 Forbidden.
        
        Scenario: Token with empty scopes list
          Given the user has a valid JWT with no scopes
          When the require_admin dependency is invoked
          Then the request is rejected with 403 Forbidden
        """
        # Arrange
        dependency = require_admin

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            dependency(token_with_no_scopes)

        # Verify 403 Forbidden
        assert exc_info.value.status_code == 403


class TestRequireScopeFactory:
    """Test cases for the require_scope factory function."""

    def test_require_scope_creates_dependency(self):
        """require_scope factory creates a callable dependency.
        
        Scenario: Create scope dependency
          Given a scope name "admin"
          When require_scope("admin") is called
          Then a callable dependency is returned
        """
        # Act
        dependency = require_scope("admin")

        # Assert
        assert callable(dependency)

    def test_require_scope_custom_scope_success(self):
        """Custom scope requirement succeeds when token has the scope.
        
        Scenario: Custom scope enforcement
          Given a token with "custom:scope"
          When a dependency requires "custom:scope"
          Then the request is authorized
        """
        # Arrange
        dependency = require_scope("custom:scope")
        token_data = {
            "client_id": "test",
            "scopes": ["custom:scope"],
            "exp": 123,
        }

        # Act
        result = dependency(token_data)

        # Assert
        assert result == token_data

    def test_require_scope_custom_scope_missing(self):
        """Custom scope requirement fails when token lacks the scope.
        
        Scenario: Missing custom scope
          Given a token without "custom:scope"
          When a dependency requires "custom:scope"
          Then the request is rejected with 403 Forbidden
        """
        # Arrange
        dependency = require_scope("custom:scope")
        token_data = {
            "client_id": "test",
            "scopes": ["other:scope"],
            "exp": 123,
        }

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            dependency(token_data)

        assert exc_info.value.status_code == 403


class TestRequireAnyScope:
    """Test cases for require_any_scope (OR logic for multiple scopes)."""

    def test_require_any_scope_admin_passes(
        self, token_with_admin_scope
    ):
        """Token with admin scope passes admin OR job:write requirement.
        
        Scenario: Multiple scope options (admin accepted)
          Given a token with "admin" scope
          When a dependency requires ("admin" OR "job:write")
          Then the request is authorized
        """
        # Arrange
        dependency = require_any_scope("admin", "job:write")

        # Act
        result = dependency(token_with_admin_scope)

        # Assert
        assert result == token_with_admin_scope

    def test_require_any_scope_job_write_passes(
        self, token_with_job_write_scope
    ):
        """Token with job:write scope passes admin OR job:write requirement.
        
        Scenario: Multiple scope options (job:write accepted)
          Given a token with "job:write" scope
          When a dependency requires ("admin" OR "job:write")
          Then the request is authorized
        """
        # Arrange
        dependency = require_any_scope("admin", "job:write")

        # Act
        result = dependency(token_with_job_write_scope)

        # Assert
        assert result == token_with_job_write_scope

    def test_require_any_scope_none_present(
        self, token_with_catalog_write_scope
    ):
        """Token with neither required scope raises 403 Forbidden.
        
        Scenario: No matching scope
          Given a token with "catalog:write" scope
          When a dependency requires ("admin" OR "job:write")
          Then the request is rejected with 403 Forbidden
        """
        # Arrange
        dependency = require_any_scope("admin", "job:write")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            dependency(token_with_catalog_write_scope)

        # Verify 403 Forbidden
        assert exc_info.value.status_code == 403
        # Error message should mention the required scopes
        detail = str(exc_info.value.detail)
        assert ("admin" in detail.lower() or "job:write" in detail.lower())


class TestPredefinedScopeDependencies:
    """Test cases for predefined scope dependency helpers."""

    def test_require_admin_or_job_write_with_admin(
        self, token_with_admin_scope
    ):
        """require_admin_or_job_write accepts admin scope.
        
        Scenario: Admin scope accepted
          Given a token with "admin" scope
          When require_admin_or_job_write is invoked
          Then the request is authorized
        """
        # Act
        result = require_admin_or_job_write(token_with_admin_scope)

        # Assert
        assert result == token_with_admin_scope

    def test_require_admin_or_job_write_with_job_write(
        self, token_with_job_write_scope
    ):
        """require_admin_or_job_write accepts job:write scope.
        
        Scenario: Job:write scope accepted
          Given a token with "job:write" scope
          When require_admin_or_job_write is invoked
          Then the request is authorized
        """
        # Act
        result = require_admin_or_job_write(token_with_job_write_scope)

        # Assert
        assert result == token_with_job_write_scope

    def test_require_admin_or_job_write_missing_both(
        self, token_with_catalog_write_scope
    ):
        """require_admin_or_job_write rejects token without either scope.
        
        Scenario: Missing both scopes
          Given a token without "admin" or "job:write"
          When require_admin_or_job_write is invoked
          Then the request is rejected with 403 Forbidden
        """
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            require_admin_or_job_write(token_with_catalog_write_scope)

        assert exc_info.value.status_code == 403

    def test_require_admin_or_catalog_write_with_admin(
        self, token_with_admin_scope
    ):
        """require_admin_or_catalog_write accepts admin scope.
        
        Scenario: Admin scope accepted
          Given a token with "admin" scope
          When require_admin_or_catalog_write is invoked
          Then the request is authorized
        """
        # Act
        result = require_admin_or_catalog_write(token_with_admin_scope)

        # Assert
        assert result == token_with_admin_scope

    def test_require_admin_or_catalog_write_with_catalog_write(
        self, token_with_catalog_write_scope
    ):
        """require_admin_or_catalog_write accepts catalog:write scope.
        
        Scenario: Catalog:write scope accepted
          Given a token with "catalog:write" scope
          When require_admin_or_catalog_write is invoked
          Then the request is authorized
        """
        # Act
        result = require_admin_or_catalog_write(token_with_catalog_write_scope)

        # Assert
        assert result == token_with_catalog_write_scope

    def test_require_admin_or_catalog_write_missing_both(
        self, token_with_job_write_scope
    ):
        """require_admin_or_catalog_write rejects token without either scope.
        
        Scenario: Missing both scopes
          Given a token without "admin" or "catalog:write"
          When require_admin_or_catalog_write is invoked
          Then the request is rejected with 403 Forbidden
        """
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            require_admin_or_catalog_write(token_with_job_write_scope)

        assert exc_info.value.status_code == 403
