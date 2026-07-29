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

"""Unit tests for generate_provision_config."""

import pytest

from backend.services.config_file_generators import generate_provision_config


class TestGenerateProvisionConfig:
    """Tests for generate_provision_config generator."""

    def test_emits_when_dns_enabled(self, tmp_path, noop_write_yaml):
        wizard_data = {"dns_enabled": True}
        generate_provision_config(wizard_data, tmp_path, noop_write_yaml)
        assert (tmp_path / "provision_config.yml").exists()

    def test_emits_when_pxe_data_present(self, tmp_path, noop_write_yaml, sample_pxe_rows):
        wizard_data = {"pxe_mapping_data": sample_pxe_rows}
        generate_provision_config(wizard_data, tmp_path, noop_write_yaml)
        assert (tmp_path / "provision_config.yml").exists()

    def test_skips_when_all_empty(self, tmp_path, noop_write_yaml):
        wizard_data = {}
        generate_provision_config(wizard_data, tmp_path, noop_write_yaml)
        assert not (tmp_path / "provision_config.yml").exists()

    def test_default_language(self, tmp_path, noop_write_yaml):
        wizard_data = {"dns_enabled": True}
        generate_provision_config(wizard_data, tmp_path, noop_write_yaml)
        content = (tmp_path / "provision_config.yml").read_text()
        assert "en_US.UTF-8" in content

    def test_default_lease_time(self, tmp_path, noop_write_yaml):
        wizard_data = {"dns_enabled": True}
        generate_provision_config(wizard_data, tmp_path, noop_write_yaml)
        content = (tmp_path / "provision_config.yml").read_text()
        assert "86400" in content

    def test_custom_kernel_version(self, tmp_path, noop_write_yaml):
        wizard_data = {"kernel_version_override": "6.12.0-55.76.1.el10_0"}
        generate_provision_config(wizard_data, tmp_path, noop_write_yaml)
        content = (tmp_path / "provision_config.yml").read_text()
        assert "6.12.0-55.76.1.el10_0" in content

    def test_skips_when_only_default_language(self, tmp_path, noop_write_yaml):
        """language=en_US.UTF-8 alone is not meaningful since it's the default."""
        wizard_data = {"language": "en_US.UTF-8"}
        generate_provision_config(wizard_data, tmp_path, noop_write_yaml)
        assert not (tmp_path / "provision_config.yml").exists()
