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

"""Unit tests for generate_security_config."""

# pylint: disable=missing-function-docstring,redefined-outer-name
from backend.services.config_file_generators import generate_security_config


class TestGenerateSecurityConfig:
    """Tests for generate_security_config generator."""

    def test_emits_ldap_connection_type(self, tmp_path, noop_write_yaml):
        wizard_data = {
            "security_config": {"ldap_connection_type": "SSL"}
        }
        generate_security_config(wizard_data, tmp_path, noop_write_yaml)
        output = tmp_path / "security_config.yml"
        assert output.exists()
        content = output.read_text()
        assert "ldap_connection_type" in content
        assert "SSL" in content

    def test_skips_when_ldap_connection_type_empty(self, tmp_path, noop_write_yaml):
        wizard_data = {"security_config": {"ldap_connection_type": ""}}
        generate_security_config(wizard_data, tmp_path, noop_write_yaml)
        assert not (tmp_path / "security_config.yml").exists()

    def test_skips_when_no_data(self, tmp_path, noop_write_yaml):
        generate_security_config({}, tmp_path, noop_write_yaml)
        assert not (tmp_path / "security_config.yml").exists()

    def test_skips_when_empty_security_config(self, tmp_path, noop_write_yaml):
        generate_security_config({"security_config": {}}, tmp_path, noop_write_yaml)
        assert not (tmp_path / "security_config.yml").exists()
