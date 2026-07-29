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

"""Unit tests for generate_user_registry_credential."""

import pytest

from backend.services.config_file_generators import generate_user_registry_credential


class TestGenerateUserRegistryCredential:
    """Tests for generate_user_registry_credential generator."""

    def test_emits_when_show_credentials_true(self, tmp_path, noop_write_yaml):
        wizard_data = {
            "_ui_showCredentials": True,
            "user_registry_credential": [
                {"name": "reg1", "username": "user1", "password": "pass1"}
            ],
        }
        generate_user_registry_credential(wizard_data, tmp_path, noop_write_yaml)
        output = tmp_path / "user_registry_credential.yml"
        assert output.exists()
        content = output.read_text()
        assert "user_registry_credential" in content
        assert "reg1" in content

    def test_skips_when_show_credentials_false(self, tmp_path, noop_write_yaml):
        wizard_data = {
            "_ui_showCredentials": False,
            "user_registry_credential": [
                {"name": "reg1", "username": "user1", "password": "pass1"}
            ],
        }
        generate_user_registry_credential(wizard_data, tmp_path, noop_write_yaml)
        assert not (tmp_path / "user_registry_credential.yml").exists()

    def test_skips_when_flag_missing(self, tmp_path, noop_write_yaml):
        generate_user_registry_credential({}, tmp_path, noop_write_yaml)
        assert not (tmp_path / "user_registry_credential.yml").exists()

    def test_management_payload_rhel(self, tmp_path, noop_write_yaml):
        wizard_data = {
            "rhel": {
                "_ui_showCredentials": True,
                "user_registry_credential": [
                    {"name": "reg2", "username": "user2", "password": "pass2"}
                ],
            }
        }
        generate_user_registry_credential(wizard_data, tmp_path, noop_write_yaml)
        output = tmp_path / "user_registry_credential.yml"
        assert output.exists()
        assert "reg2" in output.read_text()
