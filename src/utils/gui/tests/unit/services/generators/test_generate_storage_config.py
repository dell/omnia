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

"""Unit tests for generate_storage_config."""

import pytest

from backend.services.config_file_generators import generate_storage_config


class TestGenerateStorageConfig:
    """Tests for generate_storage_config generator."""

    def test_mounts_cleaned(self, tmp_path, noop_write_yaml, sample_storage_data):
        generate_storage_config(sample_storage_data, tmp_path, noop_write_yaml)
        output = tmp_path / "storage_config.yml"
        assert output.exists()
        content = output.read_text()
        assert "mounts" in content

    def test_swap_maxsize_skipped_when_not_auto(self, tmp_path, noop_write_yaml):
        wizard_data = {
            "swap": [{"filename": "/swapfile", "size": "fixed", "maxsize": "2G"}]
        }
        generate_storage_config(wizard_data, tmp_path, noop_write_yaml)
        output = tmp_path / "storage_config.yml"
        assert output.exists()
        content = output.read_text()
        assert "maxsize" not in content

    def test_swap_maxsize_kept_when_auto(self, tmp_path, noop_write_yaml):
        wizard_data = {
            "swap": [{"filename": "/swapfile", "size": "auto", "maxsize": "2G"}]
        }
        generate_storage_config(wizard_data, tmp_path, noop_write_yaml)
        content = (tmp_path / "storage_config.yml").read_text()
        assert "maxsize" in content

    def test_skips_when_no_sections(self, tmp_path, noop_write_yaml):
        generate_storage_config({}, tmp_path, noop_write_yaml)
        assert not (tmp_path / "storage_config.yml").exists()

    def test_powervault_section(self, tmp_path, noop_write_yaml, sample_storage_data):
        generate_storage_config(sample_storage_data, tmp_path, noop_write_yaml)
        content = (tmp_path / "storage_config.yml").read_text()
        assert "powervault_config" in content

    def test_preserves_octal_mode_values(self, tmp_path, noop_write_yaml):
        """Values like "0755" must stay quoted, not coerced to integer 755."""
        wizard_data = {
            "mounts": [{
                "name": "/data",
                "mode": "0755",
            }]
        }
        generate_storage_config(wizard_data, tmp_path, noop_write_yaml)
        content = (tmp_path / "storage_config.yml").read_text()
        assert '"0755"' in content
