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

"""Unit tests for generate_high_availability_config."""

# pylint: disable=missing-function-docstring,redefined-outer-name
from backend.services.config_file_generators import generate_high_availability_config


class TestGenerateHighAvailabilityConfig:
    """Tests for generate_high_availability_config generator."""

    def test_emits_when_k8s_configured(self, tmp_path, noop_write_yaml):
        wizard_data = {
            "service_k8s_cluster": [{"cluster_name": "k8s", "deployment": "rke2"}],
            "enable_ha": True,
            "service_k8s_cluster_ha": [
                {"cluster_name": "k8s", "enable_k8s_ha": True, "virtual_ip_address": "10.0.0.100"}
            ],
        }
        generate_high_availability_config(wizard_data, tmp_path, noop_write_yaml)
        output = tmp_path / "high_availability_config.yml"
        assert output.exists()
        assert "service_k8s_cluster_ha" in output.read_text()

    def test_disabled_placeholder_when_ha_off(self, tmp_path, noop_write_yaml):
        wizard_data = {
            "service_k8s_cluster": [{"cluster_name": "k8s", "deployment": "rke2"}],
            "enable_ha": False,
        }
        generate_high_availability_config(wizard_data, tmp_path, noop_write_yaml)
        output = tmp_path / "high_availability_config.yml"
        assert output.exists()
        content = output.read_text()
        assert "enable_k8s_ha" in content
        assert "false" in content.lower()

    def test_skips_when_no_k8s(self, tmp_path, noop_write_yaml):
        wizard_data = {"service_k8s_cluster": []}
        generate_high_availability_config(wizard_data, tmp_path, noop_write_yaml)
        assert not (tmp_path / "high_availability_config.yml").exists()
