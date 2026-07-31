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

"""Unit tests for generate_additional_cloud_init."""

# pylint: disable=missing-function-docstring,redefined-outer-name
from backend.services.config_file_generators import generate_additional_cloud_init


class TestGenerateAdditionalCloudInit:
    """Tests for generate_additional_cloud_init generator."""

    def test_runcmd_objects_transformed_to_strings(
        self, tmp_path, noop_write_yaml,
        sample_cloud_init_data,
    ):
        generate_additional_cloud_init(sample_cloud_init_data, tmp_path, noop_write_yaml)
        output = tmp_path / "additional_cloud_init.yml"
        assert output.exists()
        content = output.read_text()
        assert "echo hello" in content
        assert "echo world" in content

    def test_groups_keyed_by_group_name(self, tmp_path, noop_write_yaml, sample_cloud_init_data):
        generate_additional_cloud_init(sample_cloud_init_data, tmp_path, noop_write_yaml)
        content = (tmp_path / "additional_cloud_init.yml").read_text()
        assert "compute" in content
        assert "groups" in content

    def test_skips_when_empty(self, tmp_path, noop_write_yaml):
        generate_additional_cloud_init({}, tmp_path, noop_write_yaml)
        assert not (tmp_path / "additional_cloud_init.yml").exists()

    def test_common_defaults_to_empty_dict(self, tmp_path, noop_write_yaml):
        wizard_data = {
            "cloud_init_groups": [
                {
                    "group_name": "grp1",
                    "runcmd": [{"command": "ls"}],
                }
            ]
        }
        generate_additional_cloud_init(wizard_data, tmp_path, noop_write_yaml)
        content = (tmp_path / "additional_cloud_init.yml").read_text()
        assert "common" in content

    def test_groups_defaults_to_empty_dict(self, tmp_path, noop_write_yaml):
        wizard_data = {
            "cloud_init_common": {"runcmd": [{"command": "echo test"}]}
        }
        generate_additional_cloud_init(wizard_data, tmp_path, noop_write_yaml)
        content = (tmp_path / "additional_cloud_init.yml").read_text()
        assert "groups" in content

    def test_groups_runcmd_transformed(self, tmp_path, noop_write_yaml):
        wizard_data = {
            "cloud_init_groups": [
                {
                    "group_name": "compute",
                    "runcmd": [{"command": "systemctl restart test"}],
                }
            ]
        }
        generate_additional_cloud_init(wizard_data, tmp_path, noop_write_yaml)
        content = (tmp_path / "additional_cloud_init.yml").read_text()
        assert "systemctl restart test" in content
