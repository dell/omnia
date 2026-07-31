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

"""Unit tests for generate_gitlab_config."""

# pylint: disable=missing-function-docstring,redefined-outer-name
from backend.services.config_file_generators import generate_gitlab_config


class TestGenerateGitlabConfig:
    """Tests for generate_gitlab_config generator."""

    def test_skipped_when_host_empty(self, tmp_path, noop_write_yaml):
        generate_gitlab_config({"gitlab_host": ""}, tmp_path, noop_write_yaml)
        assert not (tmp_path / "gitlab_config.yml").exists()

    def test_skipped_when_host_missing(self, tmp_path, noop_write_yaml):
        generate_gitlab_config({}, tmp_path, noop_write_yaml)
        assert not (tmp_path / "gitlab_config.yml").exists()

    def test_all_keys_present_when_enabled(self, tmp_path, noop_write_yaml):
        wizard_data = {
            "gitlab_host": "gitlab.example.com",
            "gitlab_project_name": "myproject",
        }
        generate_gitlab_config(wizard_data, tmp_path, noop_write_yaml)
        output = tmp_path / "gitlab_config.yml"
        assert output.exists()
        content = output.read_text()
        for key in ("gitlab_host", "gitlab_project_name", "gitlab_project_visibility",
                     "gitlab_default_branch", "gitlab_https_port"):
            assert key in content
