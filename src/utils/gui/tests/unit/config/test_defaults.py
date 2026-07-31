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

"""Unit tests for configuration defaults."""

# pylint: disable=missing-function-docstring,redefined-outer-name
from backend.config.defaults import (
    get_build_stream_config_defaults,
    get_discovery_config_defaults,
    get_telemetry_config_defaults,
    get_telemetry_storage_config_defaults,
)


class TestGetDiscoveryConfigDefaults:
    """Tests for get_discovery_config_defaults."""

    def test_keys_present(self):
        defaults = get_discovery_config_defaults()
        assert "enable_bmc_discovery" in defaults
        assert "ome_ip" in defaults
        assert "admin_inventory_path" in defaults

    def test_bmc_discovery_disabled_by_default(self):
        defaults = get_discovery_config_defaults()
        assert defaults["enable_bmc_discovery"] is False

    def test_ome_ip_is_string(self):
        defaults = get_discovery_config_defaults()
        assert isinstance(defaults["ome_ip"], str)

    def test_admin_inventory_path_default(self):
        defaults = get_discovery_config_defaults()
        assert defaults["admin_inventory_path"] == (
            "/opt/omnia/input/project_default/admin_inventory.csv"
        )


class TestGetBuildStreamConfigDefaults:
    """Tests for get_build_stream_config_defaults."""

    def test_build_stream_disabled(self):
        defaults = get_build_stream_config_defaults()
        assert defaults["enable_build_stream"] is False

    def test_port_is_8010(self):
        defaults = get_build_stream_config_defaults()
        assert defaults["build_stream_port"] == 8010

    def test_keys_present(self):
        defaults = get_build_stream_config_defaults()
        assert "build_stream_host_ip" in defaults
        assert "aarch64_inventory_host_ip" in defaults


class TestGetTelemetryConfigDefaults:
    """Tests for get_telemetry_config_defaults."""

    def test_telemetry_sources_structure(self):
        defaults = get_telemetry_config_defaults()
        assert "telemetry_sources" in defaults
        sources = defaults["telemetry_sources"]
        for source_name in ("idrac", "ldms", "dcgm", "powerscale", "ufm", "vast", "ome"):
            assert source_name in sources

    def test_all_sources_disabled(self):
        defaults = get_telemetry_config_defaults()
        for source in defaults["telemetry_sources"].values():
            assert source["metrics_enabled"] is False

    def test_telemetry_bridges_present(self):
        defaults = get_telemetry_config_defaults()
        assert "telemetry_bridges" in defaults

    def test_telemetry_sinks_present(self):
        defaults = get_telemetry_config_defaults()
        assert "telemetry_sinks" in defaults


class TestGetTelemetryStorageConfigDefaults:
    """Tests for get_telemetry_storage_config_defaults."""

    def test_victoria_cluster_storage_present(self):
        defaults = get_telemetry_storage_config_defaults()
        assert "victoria_cluster_storage" in defaults
        vcs = defaults["victoria_cluster_storage"]
        for component in ("vmstorage", "vminsert", "vmselect", "vmagent"):
            assert component in vcs

    def test_nested_resources_structure(self):
        defaults = get_telemetry_storage_config_defaults()
        vmstorage = defaults["victoria_cluster_storage"]["vmstorage"]
        assert "resources" in vmstorage
        assert "requests" in vmstorage["resources"]
        assert "limits" in vmstorage["resources"]

    def test_csm_metrics_powerscale_storage(self):
        defaults = get_telemetry_storage_config_defaults()
        assert "csm_metrics_powerscale_storage" in defaults

    def test_kafka_storage_present(self):
        defaults = get_telemetry_storage_config_defaults()
        assert "kafka_storage" in defaults
