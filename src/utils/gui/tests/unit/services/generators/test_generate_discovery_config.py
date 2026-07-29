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

"""Unit tests for generate_discovery_config."""

import yaml
import pytest

from backend.services.config_file_generators import generate_discovery_config


class TestGenerateDiscoveryConfig:
    """Tests for generate_discovery_config generator."""

    def test_merges_user_data_with_defaults(self, tmp_path, noop_write_yaml):
        wizard_data = {
            "enable_bmc_discovery": True,
            "ome_ip": "192.168.1.100",
            "admin_inventory_path": "/custom/path.csv",
        }
        generate_discovery_config(wizard_data, tmp_path, noop_write_yaml)

        output = tmp_path / "discovery_config.yml"
        assert output.exists()
        content = output.read_text()
        assert "enable_bmc_discovery" in content
        assert "ome_ip" in content
        assert "admin_inventory_path" in content

    def test_defaults_used_when_no_user_data(self, tmp_path, noop_write_yaml):
        generate_discovery_config({}, tmp_path, noop_write_yaml)

        output = tmp_path / "discovery_config.yml"
        assert output.exists()
        content = output.read_text()
        assert "enable_bmc_discovery" in content
        assert "false" in content.lower()

    def test_admin_inventory_data_not_leaked(self, tmp_path, noop_write_yaml):
        """admin_inventory_data from Magellan flow must NOT appear in discovery_config.yml."""
        wizard_data = {
            "enable_bmc_discovery": False,
            "admin_inventory_data": [{"SERVICE_TAG": "SVC001"}],
            "admin_inventory_path": "/opt/omnia/input/project_default/admin_inventory.csv",
        }
        generate_discovery_config(wizard_data, tmp_path, noop_write_yaml)

        output = tmp_path / "discovery_config.yml"
        content = output.read_text()
        assert "admin_inventory_data" not in content
        assert "SVC001" not in content

    def test_always_emitted(self, tmp_path, noop_write_yaml):
        """discovery_config.yml is always generated, even with empty wizard data."""
        generate_discovery_config({}, tmp_path, noop_write_yaml)
        assert (tmp_path / "discovery_config.yml").exists()

    def test_user_ome_ip_overrides_default(self, tmp_path, noop_write_yaml):
        wizard_data = {"ome_ip": "10.10.10.10"}
        generate_discovery_config(wizard_data, tmp_path, noop_write_yaml)

        content = (tmp_path / "discovery_config.yml").read_text()
        assert "10.10.10.10" in content
