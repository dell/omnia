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

"""Shared fixtures for API integration tests."""

import os
from typing import Dict, Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from main import app
from infra.id_generator import UUIDv4Generator


@pytest.fixture(scope="function")
def client() -> TestClient:
    """Create test client with fresh container for each test."""
    os.environ["ENV"] = "dev"
    return TestClient(app)


@pytest.fixture(name="uuid_generator")
def uuid_generator_fixture() -> UUIDv4Generator:
    """UUID generator for test fixtures."""
    return UUIDv4Generator()


@pytest.fixture
def auth_headers(uuid_generator: UUIDv4Generator) -> Dict[str, str]:
    """Standard authentication headers for testing."""
    return {
        "Authorization": "Bearer test-client-123",
        "X-Correlation-Id": str(uuid_generator.generate()),
        "Idempotency-Key": f"test-key-{uuid_generator.generate()}",
    }


@pytest.fixture
def mock_jwt_validation() -> Generator[None, None, None]:
    """Mock JWT validation for integration tests.
    
    This fixture bypasses JWT validation to allow testing of API endpoints
    without requiring actual JWT keys.
    """
    with patch("api.auth.jwt_handler.JWTHandler.validate_token") as mock_validate:
        # Mock successful token validation
        from api.auth.jwt_handler import TokenData
        from datetime import datetime, timezone, timedelta
        
        now = datetime.now(timezone.utc)
        mock_validate.return_value = TokenData(
            client_id="test-client",
            client_name="test-client",
            scopes=["catalog:read", "catalog:write"],
            issued_at=now,
            expires_at=now + timedelta(hours=1),
            token_id="test-token-id",
        )
        yield


@pytest.fixture
def auth_headers_with_mock(mock_jwt_validation: None, uuid_generator: UUIDv4Generator) -> Dict[str, str]:
    """Authentication headers with mocked JWT validation."""
    return {
        "Authorization": "Bearer test-token",
        "X-Correlation-Id": str(uuid_generator.generate()),
        "Idempotency-Key": f"test-key-{uuid_generator.generate()}",
    }
