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

"""Unit tests for generate_build_stream_config."""

import pytest

from backend.services.config_file_generators import generate_build_stream_config


class TestGenerateBuildStreamConfig:
    """Tests for generate_build_stream_config generator."""

    def test_always_emitted(self, tmp_path, noop_write_yaml):
        generate_build_stream_config({}, tmp_path, noop_write_yaml)
        assert (tmp_path / "build_stream_config.yml").exists()

    def test_deep_merges_with_defaults(self, tmp_path, noop_write_yaml):
        wizard_data = {"enable_build_stream": True, "build_stream_port": 9999}
        generate_build_stream_config(wizard_data, tmp_path, noop_write_yaml)
        content = (tmp_path / "build_stream_config.yml").read_text()
        assert "9999" in content

    def test_defaults_when_empty_data(self, tmp_path, noop_write_yaml):
        generate_build_stream_config({}, tmp_path, noop_write_yaml)
        content = (tmp_path / "build_stream_config.yml").read_text()
        assert "enable_build_stream" in content
        assert "8010" in content
