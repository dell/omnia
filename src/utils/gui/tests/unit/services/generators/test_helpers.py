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

"""Unit tests for config_file_generators helper functions."""

import pytest
import yaml

from backend.services.config_file_generators import (
    has_meaningful_data,
    _deep_merge,
    _write_config_file,
    _clean_storage_entries,
)


class TestHasMeaningfulData:
    """Tests for has_meaningful_data helper."""

    def test_none_returns_false(self):
        assert has_meaningful_data(None) is False

    def test_empty_string_returns_false(self):
        assert has_meaningful_data("") is False

    def test_whitespace_only_returns_false(self):
        assert has_meaningful_data("   ") is False

    def test_empty_dict_returns_false(self):
        assert has_meaningful_data({}) is False

    def test_empty_list_returns_false(self):
        assert has_meaningful_data([]) is False

    def test_false_returns_false(self):
        assert has_meaningful_data(False) is False

    def test_list_of_empty_strings_returns_false(self):
        assert has_meaningful_data(["", ""]) is False

    def test_nested_empty_dict_returns_false(self):
        assert has_meaningful_data({"a": {}, "b": []}) is False

    def test_nonempty_string_returns_true(self):
        assert has_meaningful_data("hello") is True

    def test_true_returns_true(self):
        assert has_meaningful_data(True) is True

    def test_zero_returns_true(self):
        assert has_meaningful_data(0) is True

    def test_integer_returns_true(self):
        assert has_meaningful_data(42) is True

    def test_float_returns_true(self):
        assert has_meaningful_data(3.14) is True

    def test_nested_dict_with_value_returns_true(self):
        assert has_meaningful_data({"a": {"b": "val"}}) is True

    def test_list_with_one_nonempty_returns_true(self):
        assert has_meaningful_data(["", "hello"]) is True


class TestDeepMerge:
    """Tests for _deep_merge helper."""

    def test_override_wins(self):
        base = {"a": 1, "b": 2}
        override = {"b": 99}
        _deep_merge(base, override)
        assert base == {"a": 1, "b": 99}

    def test_nested_merge(self):
        base = {"a": {"x": 1, "y": 2}}
        override = {"a": {"y": 99, "z": 3}}
        _deep_merge(base, override)
        assert base == {"a": {"x": 1, "y": 99, "z": 3}}

    def test_new_keys_added(self):
        base = {"a": 1}
        override = {"b": 2}
        _deep_merge(base, override)
        assert base == {"a": 1, "b": 2}

    def test_base_keys_preserved(self):
        base = {"a": 1, "b": 2, "c": 3}
        override = {"b": 99}
        _deep_merge(base, override)
        assert base["a"] == 1
        assert base["c"] == 3

    def test_override_replaces_non_dict_with_dict(self):
        base = {"a": "string"}
        override = {"a": {"nested": True}}
        _deep_merge(base, override)
        assert base == {"a": {"nested": True}}


class TestWriteConfigFile:
    """Tests for _write_config_file helper."""

    def test_writes_yaml_to_path(self, tmp_path):
        config = {"key1": "value1", "key2": 42}
        path = tmp_path / "test.yml"
        _write_config_file(path, config)
        assert path.exists()
        content = path.read_text()
        assert "key1:" in content
        assert "key2:" in content

    def test_creates_parent_dirs(self, tmp_path):
        config = {"key": "val"}
        path = tmp_path / "sub" / "dir" / "test.yml"
        _write_config_file(path, config)
        assert path.exists()

    def test_quoted_strings_when_enabled(self, tmp_path):
        config = {"host": "10.0.0.1"}
        path = tmp_path / "quoted.yml"
        _write_config_file(path, config, quote_all_strings=True)
        content = path.read_text()
        assert '"10.0.0.1"' in content

    def test_top_level_keys_present(self, tmp_path):
        config = {"alpha": "a", "beta": {"nested": "b"}, "gamma": [1, 2]}
        path = tmp_path / "multi.yml"
        _write_config_file(path, config)
        content = path.read_text()
        assert "alpha:" in content
        assert "beta:" in content
        assert "gamma:" in content


class TestCleanStorageEntries:
    """Tests for _clean_storage_entries helper."""

    def test_filters_by_required_key(self):
        entries = [
            {"name": "mount1", "path": "/home"},
            {"path": "/tmp"},  # missing required 'name'
        ]
        result = _clean_storage_entries(entries, "name", set())
        assert len(result) == 1
        assert result[0]["name"] == "mount1"

    def test_splits_comma_separated_array_fields(self):
        entries = [{"name": "m1", "groups": "g1,g2,g3"}]
        result = _clean_storage_entries(entries, "name", {"groups"})
        assert result[0]["groups"] == ["g1", "g2", "g3"]

    def test_skip_fn_callback_honored(self):
        entries = [{"filename": "/swap", "size": "fixed", "maxsize": "2G"}]
        result = _clean_storage_entries(
            entries,
            "filename",
            set(),
            skip_fn=lambda k, e: k == "maxsize" and e.get("size") != "auto",
        )
        assert len(result) == 1
        assert "maxsize" not in result[0]

    def test_skip_fn_not_triggered_when_condition_met(self):
        entries = [{"filename": "/swap", "size": "auto", "maxsize": "2G"}]
        result = _clean_storage_entries(
            entries,
            "filename",
            set(),
            skip_fn=lambda k, e: k == "maxsize" and e.get("size") != "auto",
        )
        assert result[0]["maxsize"] == "2G"

    def test_empty_values_removed(self):
        entries = [{"name": "m1", "opt1": "", "opt2": None, "opt3": [], "opt4": {}}]
        result = _clean_storage_entries(entries, "name", set())
        assert result[0] == {"name": "m1"}
