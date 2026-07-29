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

"""Unit tests for generate_local_repo_config."""

import pytest

from backend.services.config_file_generators import generate_local_repo_config


class TestGenerateLocalRepoConfig:
    """Tests for generate_local_repo_config generator."""

    def test_rhel_section_processing(self, tmp_path, noop_write_yaml):
        wizard_data = {
            "rhel": {
                "_ui_showRhelRepos": True,
                "rhel_os_url_x86_64": "http://repo.example.com/rhel/x86_64",
            },
        }
        generate_local_repo_config(wizard_data, tmp_path, noop_write_yaml)
        output = tmp_path / "local_repo_config.yml"
        assert output.exists()
        content = output.read_text()
        assert "rhel_os_url_x86_64" in content

    def test_ubuntu_ignored(self, tmp_path, noop_write_yaml):
        """Ubuntu is disabled for later release."""
        wizard_data = {
            "ubuntu": {
                "_ui_showUbuntuRepos": True,
                "ubuntu_os_url_x86_64": "http://repo.example.com/ubuntu/x86_64",
            },
        }
        generate_local_repo_config(wizard_data, tmp_path, noop_write_yaml)
        assert not (tmp_path / "local_repo_config.yml").exists()

    def test_skips_when_no_meaningful_data(self, tmp_path, noop_write_yaml):
        wizard_data = {"rhel": {}}
        generate_local_repo_config(wizard_data, tmp_path, noop_write_yaml)
        assert not (tmp_path / "local_repo_config.yml").exists()

    def test_legacy_payload(self, tmp_path, noop_write_yaml):
        """Legacy single-OS payload without 'rhel' top-level key."""
        wizard_data = {
            "_ui_showRhelRepos": True,
            "rhel_os_url_x86_64": "http://repo.example.com/rhel/x86_64",
        }
        generate_local_repo_config(wizard_data, tmp_path, noop_write_yaml)
        output = tmp_path / "local_repo_config.yml"
        assert output.exists()
