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

"""Unit tests for generate_network_spec."""

import pytest

from backend.services.config_file_generators import generate_network_spec


class TestGenerateNetworkSpec:
    """Tests for generate_network_spec generator."""

    def test_writes_filtered_networks(self, tmp_path, noop_write_yaml, sample_network_data):
        wizard_data = {"Networks": sample_network_data}
        generate_network_spec(wizard_data, tmp_path, noop_write_yaml)
        output = tmp_path / "network_spec.yml"
        assert output.exists()
        content = output.read_text()
        assert "Networks" in content
        assert "admin_network" in content
        assert "oim_nic_name" in content
        assert "eno1" in content
        assert "subnet" in content
        assert "netmask_bits" in content
        assert "primary_oim_admin_ip" in content
        assert "dynamic_range" in content

    def test_skips_empty_ib_subnet(self, tmp_path, noop_write_yaml):
        wizard_data = {
            "Networks": [{"ib_network": {"subnet": ""}}]
        }
        generate_network_spec(wizard_data, tmp_path, noop_write_yaml)
        assert not (tmp_path / "network_spec.yml").exists()

    def test_skips_when_no_data(self, tmp_path, noop_write_yaml):
        generate_network_spec({}, tmp_path, noop_write_yaml)
        assert not (tmp_path / "network_spec.yml").exists()

    def test_skips_empty_networks_list(self, tmp_path, noop_write_yaml):
        generate_network_spec({"Networks": []}, tmp_path, noop_write_yaml)
        assert not (tmp_path / "network_spec.yml").exists()
