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

"""Unit tests for generate_telemetry_storage_config."""

# pylint: disable=missing-function-docstring,redefined-outer-name
from backend.services.config_file_generators import (
    generate_telemetry_storage_config,
    _flatten_csm_metrics_powerscale_storage,
)


class TestGenerateTelemetryStorageConfig:
    """Tests for generate_telemetry_storage_config generator."""

    def test_always_emitted(self, tmp_path, noop_write_yaml):
        generate_telemetry_storage_config({}, tmp_path, noop_write_yaml)
        assert (tmp_path / "telemetry_storage_config.yml").exists()

    def test_deep_merges_with_defaults(self, tmp_path, noop_write_yaml):
        wizard_data = {
            "victoria_cluster_storage": {
                "vmstorage": {"replicas": 5}
            }
        }
        generate_telemetry_storage_config(wizard_data, tmp_path, noop_write_yaml)
        content = (tmp_path / "telemetry_storage_config.yml").read_text()
        assert "5" in content


class TestFlattenCsmMetricsPowerscaleStorage:
    """Tests for _flatten_csm_metrics_powerscale_storage helper."""

    def test_flattens_resources_wrapper(self):
        config = {
            "csm_metrics_powerscale_storage": {
                "resources": {
                    "requests": {"cpu": "200m", "memory": "256Mi"},
                    "limits": {"cpu": "1000m", "memory": "1Gi"},
                }
            }
        }
        _flatten_csm_metrics_powerscale_storage(config)
        section = config["csm_metrics_powerscale_storage"]
        assert "resources" not in section
        assert section["requests"]["cpu"] == "200m"
        assert section["limits"]["memory"] == "1Gi"

    def test_noop_when_no_resources_key(self):
        config = {
            "csm_metrics_powerscale_storage": {
                "requests": {"cpu": "100m"},
            }
        }
        _flatten_csm_metrics_powerscale_storage(config)
        assert config["csm_metrics_powerscale_storage"]["requests"]["cpu"] == "100m"

    def test_noop_when_section_missing(self):
        config = {}
        _flatten_csm_metrics_powerscale_storage(config)
        assert config == {}
