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

"""Unit tests for API dependencies."""

import pytest
from fastapi import HTTPException

from api.dependencies import get_client_id, get_idempotency_key
from core.jobs.value_objects import ClientId


class TestGetClientId:
    """Tests for get_client_id dependency function."""

    def test_valid_token_data_returns_client_id(self):
        """Valid token data should return ClientId."""
        token_data = {"client_id": "test-client-123"}

        client_id = get_client_id(token_data)

        assert isinstance(client_id, ClientId)
        assert client_id.value == "test-client-123"

    def test_token_data_with_different_client(self):
        """Token data with different client should return correct ClientId."""
        token_data = {"client_id": "another-client"}

        client_id = get_client_id(token_data)

        assert client_id.value == "another-client"

    def test_missing_client_id_raises_error(self):
        """Missing client_id key should raise KeyError."""
        token_data = {"scopes": ["job:write"]}

        with pytest.raises(KeyError):
            get_client_id(token_data)

    def test_empty_client_id_raises_value_error(self):
        """Empty client_id should raise ValueError from ClientId validation."""
        token_data = {"client_id": ""}

        with pytest.raises(ValueError):
            get_client_id(token_data)


class TestGetIdempotencyKey:
    """Tests for get_idempotency_key dependency function."""

    def test_valid_idempotency_key_returned(self):
        """Valid idempotency key should be returned unchanged."""
        key = "test-key-12345"

        result = get_idempotency_key(key)

        assert result == "test-key-12345"

    def test_idempotency_key_with_special_chars(self):
        """Idempotency key with special characters should be accepted."""
        key = "test-key-abc-123_xyz"

        result = get_idempotency_key(key)

        assert result == "test-key-abc-123_xyz"

    def test_empty_idempotency_key_raises_422(self):
        """Empty idempotency key should raise 422 HTTPException."""
        key = ""

        with pytest.raises(HTTPException) as exc_info:
            get_idempotency_key(key)

        assert exc_info.value.status_code == 422

    def test_whitespace_only_key_raises_422(self):
        """Whitespace-only idempotency key should raise 422 HTTPException."""
        key = "   "

        with pytest.raises(HTTPException) as exc_info:
            get_idempotency_key(key)

        assert exc_info.value.status_code == 422

    def test_key_exceeding_max_length_raises_422(self):
        """Key exceeding max length should raise 422 HTTPException."""
        key = "a" * 256

        with pytest.raises(HTTPException) as exc_info:
            get_idempotency_key(key)

        assert exc_info.value.status_code == 422
        assert "length" in exc_info.value.detail.lower()

    def test_key_at_max_length_accepted(self):
        """Key at max length should be accepted."""
        key = "a" * 255

        result = get_idempotency_key(key)

        assert result == key
        assert len(result) == 255
