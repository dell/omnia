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

"""Unit tests for file I/O utilities."""

# pylint: disable=missing-function-docstring,redefined-outer-name
import json
import yaml
import pytest

from backend.utils.file_io import read_json, write_json, write_yaml, ensure_directory


class TestReadJson:
    """Tests for read_json."""

    def test_valid_file_returns_dict(self, tmp_path):
        data = {"key": "value", "num": 42}
        path = tmp_path / "test.json"
        path.write_text(json.dumps(data))
        result = read_json(path)
        assert result == data

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            read_json(tmp_path / "nonexistent.json")

    def test_invalid_json_raises(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{invalid json")
        with pytest.raises(json.JSONDecodeError):
            read_json(path)


class TestWriteJson:
    """Tests for write_json."""

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "sub" / "dir" / "out.json"
        write_json(path, {"key": "val"})
        assert path.exists()

    def test_round_trip(self, tmp_path):
        data = {"alpha": 1, "beta": [2, 3], "gamma": {"nested": True}}
        path = tmp_path / "round_trip.json"
        write_json(path, data)
        with open(path, encoding='utf-8') as f:
            loaded = json.load(f)
        assert loaded == data


class TestWriteYaml:
    """Tests for write_yaml."""

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "sub" / "dir" / "out.yml"
        write_yaml(path, {"key": "val"})
        assert path.exists()

    def test_round_trip(self, tmp_path):
        data = {"alpha": 1, "beta": [2, 3], "gamma": {"nested": True}}
        path = tmp_path / "round_trip.yml"
        write_yaml(path, data)
        with open(path, encoding='utf-8') as f:
            loaded = yaml.safe_load(f)
        assert loaded == data


class TestEnsureDirectory:
    """Tests for ensure_directory."""

    def test_creates_nested_dirs(self, tmp_path):
        target = tmp_path / "a" / "b" / "c"
        ensure_directory(target)
        assert target.is_dir()

    def test_no_error_if_exists(self, tmp_path):
        target = tmp_path / "existing"
        target.mkdir()
        ensure_directory(target)  # should not raise
        assert target.is_dir()
