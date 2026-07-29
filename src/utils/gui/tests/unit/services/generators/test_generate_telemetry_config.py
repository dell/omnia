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

"""Unit tests for generate_telemetry_config."""

import pytest

from backend.services.config_file_generators import generate_telemetry_config


class TestGenerateTelemetryConfig:
    """Tests for generate_telemetry_config generator."""

    def test_always_emitted(self, tmp_path, noop_write_yaml):
        generate_telemetry_config({}, tmp_path, noop_write_yaml)
        assert (tmp_path / "telemetry_config.yml").exists()

    def test_deep_merges_with_defaults(self, tmp_path, noop_write_yaml):
        wizard_data = {
            "telemetry_sources": {"idrac": {"metrics_enabled": True}}
        }
        generate_telemetry_config(wizard_data, tmp_path, noop_write_yaml)
        content = (tmp_path / "telemetry_config.yml").read_text()
        assert "telemetry_sources" in content
    def test_default_sources_preserved_after_merge(self, tmp_path, noop_write_yaml):
        wizard_data = {
            "telemetry_sources": {"idrac": {"metrics_enabled": True}}
        }
        generate_telemetry_config(wizard_data, tmp_path, noop_write_yaml)
        content = (tmp_path / "telemetry_config.yml").read_text()
        for source in ("ldms", "dcgm", "powerscale", "ufm", "vast", "ome"):
            assert source in content, f"{source} should be preserved from defaults"

    def test_user_override_wins(self, tmp_path, noop_write_yaml):
        wizard_data = {
            "telemetry_sources": {"idrac": {"metrics_enabled": True}}
        }
        generate_telemetry_config(wizard_data, tmp_path, noop_write_yaml)
        content = (tmp_path / "telemetry_config.yml").read_text()
        assert "metrics_enabled" in content
        assert "true" in content

    def test_non_dict_values_ignored(self, tmp_path, noop_write_yaml):
        wizard_data = {
            "telemetry_sources": "not_a_dict",
            "some_string_key": "value",
        }
        generate_telemetry_config(wizard_data, tmp_path, noop_write_yaml)
        content = (tmp_path / "telemetry_config.yml").read_text()
        assert "not_a_dict" not in content
        assert "some_string_key" not in content
