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

Tests the scope guards used by the job and catalog routes. The ``admin``
scope is not grantable (see ``api.auth.scopes``), so no guard accepts it.

Test coverage:
- TC-UT-007: scope enforcement and authorization failure handling
"""

import pytest
from fastapi import HTTPException

from api.auth.scopes import GRANTABLE_SCOPES
from api.dependencies import (
    require_any_scope,
    require_catalog_read,
    require_catalog_write,
    require_job_read,
    require_job_write,
    require_scope,
)


def _token(*scopes):
    return {"client_id": "test-client", "scopes": list(scopes), "exp": 1234567890}


@pytest.fixture
def token_with_job_write_scope():
    """Token data with job:write scope."""
    return _token("job:write")


@pytest.fixture
def token_with_job_read_scope():
    """Token data with job:read scope."""
    return _token("job:read")


@pytest.fixture
def token_with_catalog_write_scope():
    """Token data with catalog:write scope."""
    return _token("catalog:write")


@pytest.fixture
def token_with_catalog_read_scope():
    """Token data with catalog:read scope."""
    return _token("catalog:read")


@pytest.fixture
def token_with_admin_scope():
    """Token data carrying the non-grantable admin scope."""
    return _token("admin", "admin:write")


@pytest.fixture
def token_with_no_scopes():
    """Token data with empty scopes list."""
    return _token()


class TestScopeVocabulary:
    """The grantable scope list is the single source of truth."""

    def test_grantable_scopes_exclude_admin(self):
        """No admin scope can be granted."""
        assert GRANTABLE_SCOPES == {
            "catalog:read", "catalog:write", "job:read", "job:write",
        }
        assert not any(s.startswith("admin") for s in GRANTABLE_SCOPES)

    def test_registration_rejects_unknown_scope_without_echoing_it(self):
        """The validation message lists allowed scopes, never the raw value."""
        from api.auth.schemas import ClientRegistrationRequest  # pylint: disable=import-outside-toplevel
        from pydantic import ValidationError  # pylint: disable=import-outside-toplevel

        raw = "x" * 5000 + "\r\nINJECTED"
        with pytest.raises(ValidationError) as exc_info:
            ClientRegistrationRequest(client_name="ci", allowed_scopes=[raw])
        message = exc_info.value.errors()[0]["msg"]
        assert "INJECTED" not in message
        assert len(message) < 200
        assert "job:write" in message

    def test_registration_accepts_grantable_scopes(self):
        """Every grantable scope is still accepted."""
        from api.auth.schemas import ClientRegistrationRequest  # pylint: disable=import-outside-toplevel

        request = ClientRegistrationRequest(
            client_name="ci", allowed_scopes=sorted(GRANTABLE_SCOPES)
        )
        assert set(request.allowed_scopes) == set(GRANTABLE_SCOPES)


class TestRequireJobWrite:
    """require_job_write guards job create, delete and upload."""

    def test_job_write_accepted(self, token_with_job_write_scope):
        """job:write passes."""
        assert require_job_write(token_with_job_write_scope) == token_with_job_write_scope

    @pytest.mark.parametrize(
        "fixture_name",
        [
            "token_with_job_read_scope",
            "token_with_catalog_write_scope",
            "token_with_admin_scope",
            "token_with_no_scopes",
        ],
    )
    def test_other_scopes_rejected(self, fixture_name, request):
        """Anything other than job:write is a 403."""
        with pytest.raises(HTTPException) as exc_info:
            require_job_write(request.getfixturevalue(fixture_name))
        assert exc_info.value.status_code == 403


class TestRequireJobRead:
    """require_job_read guards job and artifact reads."""

    def test_job_read_accepted(self, token_with_job_read_scope):
        """job:read passes."""
        assert require_job_read(token_with_job_read_scope) == token_with_job_read_scope

    def test_job_write_accepted(self, token_with_job_write_scope):
        """job:write also allows reads."""
        assert require_job_read(token_with_job_write_scope) == token_with_job_write_scope

    @pytest.mark.parametrize(
        "fixture_name",
        [
            "token_with_catalog_read_scope",
            "token_with_catalog_write_scope",
            "token_with_admin_scope",
            "token_with_no_scopes",
        ],
    )
    def test_other_scopes_rejected(self, fixture_name, request):
        """Tokens without a job scope are a 403."""
        with pytest.raises(HTTPException) as exc_info:
            require_job_read(request.getfixturevalue(fixture_name))
        assert exc_info.value.status_code == 403


class TestRequireCatalogScopes:
    """Catalog guards keep their exact-scope behaviour."""

    def test_catalog_read(self, token_with_catalog_read_scope):
        """catalog:read passes the read guard."""
        assert require_catalog_read(token_with_catalog_read_scope)

    def test_catalog_write(self, token_with_catalog_write_scope):
        """catalog:write passes the write guard."""
        assert require_catalog_write(token_with_catalog_write_scope)

    def test_catalog_write_rejects_job_write(self, token_with_job_write_scope):
        """A job scope does not open catalog writes."""
        with pytest.raises(HTTPException) as exc_info:
            require_catalog_write(token_with_job_write_scope)
        assert exc_info.value.status_code == 403


class TestRequireScopeFactory:
    """Test cases for the require_scope factory function."""

    def test_require_scope_creates_dependency(self):
        """require_scope factory creates a callable dependency."""
        assert callable(require_scope("job:write"))

    def test_require_scope_custom_scope_success(self):
        """Custom scope requirement succeeds when token has the scope."""
        dependency = require_scope("custom:scope")
        token_data = _token("custom:scope")
        assert dependency(token_data) == token_data

    def test_require_scope_custom_scope_missing(self):
        """Custom scope requirement fails when token lacks the scope."""
        dependency = require_scope("custom:scope")
        with pytest.raises(HTTPException) as exc_info:
            dependency(_token("other:scope"))
        assert exc_info.value.status_code == 403

    def test_require_scope_empty_scopes(self, token_with_no_scopes):
        """A token with no scopes is rejected."""
        with pytest.raises(HTTPException) as exc_info:
            require_scope("job:write")(token_with_no_scopes)
        assert exc_info.value.status_code == 403


class TestRequireAnyScope:
    """Test cases for require_any_scope (OR logic for multiple scopes)."""

    def test_first_scope_passes(self, token_with_job_read_scope):
        """A token with the first scope passes."""
        dependency = require_any_scope("job:read", "job:write")
        assert dependency(token_with_job_read_scope) == token_with_job_read_scope

    def test_second_scope_passes(self, token_with_job_write_scope):
        """A token with the second scope passes."""
        dependency = require_any_scope("job:read", "job:write")
        assert dependency(token_with_job_write_scope) == token_with_job_write_scope

    def test_none_present(self, token_with_catalog_write_scope):
        """A token with neither scope raises 403 naming the scopes."""
        dependency = require_any_scope("job:read", "job:write")
        with pytest.raises(HTTPException) as exc_info:
            dependency(token_with_catalog_write_scope)
        assert exc_info.value.status_code == 403
        detail = str(exc_info.value.detail).lower()
        assert "job:read" in detail or "job:write" in detail
