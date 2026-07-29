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

"""Unit tests for WizardGeneratorService."""

import pytest

from backend.services.wizard_generator_service import (
    GENERATED_CONFIG_FILENAMES,
    WizardGeneratorService,
)
from backend.core.exceptions import GenerationError


class TestGeneratedConfigFilenames:
    """Tests for the GENERATED_CONFIG_FILENAMES constant."""

    def test_admin_inventory_in_list(self):
        assert "admin_inventory.csv" in GENERATED_CONFIG_FILENAMES

    def test_pxe_mapping_in_list(self):
        assert "pxe_mapping_file.csv" in GENERATED_CONFIG_FILENAMES

    def test_all_expected_filenames_present(self):
        expected = [
            "pxe_mapping_file.csv",
            "provision_config.yml",
            "omnia_config.yml",
            "network_spec.yml",
            "gitlab_config.yml",
            "build_stream_config.yml",
            "discovery_config.yml",
            "high_availability_config.yml",
            "telemetry_config.yml",
            "telemetry_storage_config.yml",
            "user_registry_credential.yml",
            "storage_config.yml",
            "additional_cloud_init.yml",
            "security_config.yml",
            "admin_inventory.csv",
        ]
        assert len(GENERATED_CONFIG_FILENAMES) == len(expected)
        for name in expected:
            assert name in GENERATED_CONFIG_FILENAMES

    def test_count_is_15(self):
        assert len(GENERATED_CONFIG_FILENAMES) == 15


class TestGenerateAllConfigs:
    """Tests for WizardGeneratorService.generate_all_configs."""

    def test_raises_when_no_wizard_data(self, tmp_path):
        settings = type("Settings", (), {"output_dir": tmp_path})()
        service = WizardGeneratorService(settings=settings)
        with pytest.raises(GenerationError, match="No wizard data"):
            service.generate_all_configs(wizard_data=None)

    def test_raises_when_empty_wizard_data(self, tmp_path):
        settings = type("Settings", (), {"output_dir": tmp_path})()
        service = WizardGeneratorService(settings=settings)
        with pytest.raises(GenerationError):
            service.generate_all_configs(wizard_data={})

    def test_returns_result_with_valid_data(self, tmp_path, sample_wizard_data):
        settings = type("Settings", (), {"output_dir": tmp_path})()
        service = WizardGeneratorService(settings=settings)
        result = service.generate_all_configs(wizard_data=sample_wizard_data, output_dir=tmp_path)
        assert result["config_files_generated"] is True
        assert "input_dir" in result


class TestSelectiveGeneration:
    """Tests for files_to_generate filtering."""

    def test_only_selected_files_generated(self, tmp_path, sample_wizard_data):
        settings = type("Settings", (), {"output_dir": tmp_path})()
        service = WizardGeneratorService(settings=settings)
        sample_wizard_data["files_to_generate"] = ["discovery_config.yml"]
        result = service.generate_all_configs(wizard_data=sample_wizard_data, output_dir=tmp_path)
        assert result["config_files_generated"] is True
        # discovery_config is always generated
        assert (tmp_path / "discovery_config.yml").exists()
        # Files not selected should not be generated
        assert not (tmp_path / "omnia_config.yml").exists()
        assert not (tmp_path / "admin_inventory.csv").exists()
