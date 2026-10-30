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

"""Tokens stop working once their client is deleted or disabled."""

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from api.auth.jwt_handler import TokenData
from api.dependencies import verify_token
from api.vault_client import VaultClient, VaultDecryptError

CLIENT_ID = "bld_0123456789abcdef0123456789abcdef"


def _jwt_handler():
    now = datetime.now(timezone.utc)
    handler = MagicMock()
    handler.validate_token.return_value = TokenData(
        client_id=CLIENT_ID,
        client_name="ci",
        scopes=["job:write"],
        issued_at=now,
        expires_at=now + timedelta(hours=1),
        token_id="jti-1",
    )
    return handler


def _vault(clients=None, error=None):
    vault = MagicMock()
    if error:
        vault.get_oauth_clients_cached.side_effect = error
    else:
        vault.get_oauth_clients_cached.return_value = clients or {}
    return vault


def _verify(vault):
    return verify_token(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials="token"),
        _jwt_handler(),
        vault,
    )


@pytest.mark.unit
class TestTokenRequiresActiveClient:
    """verify_token accepts a valid JWT only while its client is active."""

    def test_active_client_accepted(self):
        """A valid token for an active client is accepted."""
        result = _verify(_vault({CLIENT_ID: {"is_active": True}}))
        assert result["client_id"] == CLIENT_ID
        assert result["token_id"] == "jti-1"

    @pytest.mark.parametrize(
        "clients",
        [
            {},
            {CLIENT_ID: {"is_active": False}},
            {CLIENT_ID: {}},
            {"bld_other": {"is_active": True}},
        ],
        ids=["deleted", "disabled", "no-active-flag", "other-client-only"],
    )
    def test_deleted_or_disabled_client_rejected(self, clients):
        """A valid token is rejected once its client is gone or disabled."""
        with pytest.raises(HTTPException) as exc_info:
            _verify(_vault(clients))
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail["error"] == "invalid_token"

    def test_unreadable_registry_fails_closed(self):
        """If the client registry cannot be read, the token is rejected."""
        with pytest.raises(HTTPException) as exc_info:
            _verify(_vault(error=VaultDecryptError("bad vault")))
        assert exc_info.value.status_code == 401


@pytest.mark.unit
class TestOAuthClientsCache:
    """The client registry is decrypted again only when the vault file changes."""

    def test_reads_once_until_file_changes(self, tmp_path):
        """The vault is decrypted once, then again only after the file changes."""
        vault_file = tmp_path / "creds.yml"
        vault_file.write_text("v1", encoding="utf-8")
        client = VaultClient(oauth_clients_vault_path=str(vault_file))
        with patch.object(
            client, "get_oauth_clients",
            side_effect=[{CLIENT_ID: {"is_active": True}}, {}],
        ) as read:
            assert CLIENT_ID in client.get_oauth_clients_cached()
            assert CLIENT_ID in client.get_oauth_clients_cached()
            assert read.call_count == 1

            vault_file.write_text("v2-client-removed", encoding="utf-8")
            stat = vault_file.stat()
            os.utime(vault_file, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))

            assert not client.get_oauth_clients_cached()
            assert read.call_count == 2

    def test_missing_file_returns_no_clients(self, tmp_path):
        """A missing vault file means no registered clients."""
        client = VaultClient(oauth_clients_vault_path=str(tmp_path / "absent.yml"))
        with patch.object(client, "get_oauth_clients") as read:
            assert not client.get_oauth_clients_cached()
        read.assert_not_called()
