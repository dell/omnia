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

"""Auth API integration fixtures using mock vault credentials."""

import base64
from typing import Dict

import pytest

from tests.mocks.mock_vault_client import MockVaultClient


@pytest.fixture
def valid_auth_header() -> Dict[str, str]:
    """Create valid Basic Auth header for registration endpoint."""
    credentials = base64.b64encode(
        f"{MockVaultClient.DEFAULT_TEST_USERNAME}:{MockVaultClient.DEFAULT_TEST_PASSWORD}".encode()
    ).decode()
    return {"Authorization": f"Basic {credentials}"}


@pytest.fixture
def invalid_auth_header() -> Dict[str, str]:
    """Create invalid Basic Auth header."""
    credentials = base64.b64encode(b"wrong_user:wrong_password").decode()
    return {"Authorization": f"Basic {credentials}"}
