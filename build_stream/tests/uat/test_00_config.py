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

"""UAT tests for configuration loading."""

import pytest


@pytest.mark.uat
class TestConfiguration:
    """Test UAT configuration is loaded correctly."""

    def test_base_url_configuration(self, base_url: str):
        """Test base URL is configured correctly."""
        assert base_url is not None
        assert base_url.startswith(("http://", "https://"))
        assert len(base_url) > 0
        print(f"✅ Base URL configured: {base_url}")

    def test_auth_username_configuration(self, auth_username: str):
        """Test auth username is configured correctly."""
        assert auth_username is not None
        assert len(auth_username) > 0
        print(f"✅ Auth username configured: {auth_username}")

    def test_auth_password_configuration(self, auth_password: str):
        """Test auth password is loaded from environment."""
        assert auth_password is not None
        assert len(auth_password) > 0
        print(f"✅ Auth password loaded from environment: {'*' * len(auth_password)}")

    def test_client_name_configuration(self, client_name: str):
        """Test client name is configured correctly."""
        assert client_name is not None
        assert len(client_name) > 0
        print(f"✅ Client name configured: {client_name}")

    def test_client_scopes_configuration(self, client_scopes: list):
        """Test client scopes are configured correctly."""
        assert client_scopes is not None
        assert len(client_scopes) > 0
        # Verify scopes contain expected basic permissions
        assert all(isinstance(scope, str) for scope in client_scopes)
        assert all(len(scope) > 0 for scope in client_scopes)
        print(f"✅ Client scopes configured: {client_scopes}")

    def test_client_id_configuration(self, client_id: str):
        """Test client ID is configured correctly."""
        assert client_id is not None
        assert len(client_id) > 0
        assert client_id.startswith("bld_")
        print(f"✅ Client ID configured: {client_id[:10]}...")

    def test_client_secret_configuration(self, client_secret: str):
        """Test client secret is configured correctly."""
        assert client_secret is not None
        assert len(client_secret) > 0
        assert client_secret.startswith("bld_s_")
        print(f"✅ Client secret configured: {client_secret[:10]}...")
