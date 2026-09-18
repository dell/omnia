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

"""Unit tests for Local Repository value objects."""

import pytest

from core.localrepo.value_objects import (
    ExecutionTimeout,
    ExtraVars,
    PlaybookPath,
)


class TestPlaybookPath:
    """Tests for PlaybookPath value object."""

    def test_valid_playbook_path(self):
        """Valid playbook filename should be accepted."""
        path = PlaybookPath("local_repo.yml")
        assert str(path) == "local_repo.yml"

    def test_valid_yaml_extension(self):
        """Filename with .yaml extension should be accepted."""
        path = PlaybookPath("test.yaml")
        assert str(path) == "test.yaml"

    def test_empty_path_raises(self):
        """Empty path should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            PlaybookPath("")

    def test_whitespace_path_raises(self):
        """Whitespace-only path should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            PlaybookPath("   ")

    def test_relative_path_raises(self):
        """Relative path should raise ValueError."""
        with pytest.raises(ValueError, match="Playbook name cannot contain path separators"):
            PlaybookPath("relative/path.yml")

    def test_path_traversal_raises(self):
        """Path with traversal should raise ValueError."""
        with pytest.raises(ValueError, match="Path traversal not allowed"):
            PlaybookPath("../etc/passwd.yml")

    def test_non_yaml_extension_raises(self):
        """Non-YAML extension should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid playbook name format"):
            PlaybookPath("playbook.txt")

    def test_path_exceeds_max_length(self):
        """Path exceeding max length should raise ValueError."""
        long_name = "a" * 250 + ".yml"
        with pytest.raises(ValueError, match="cannot exceed"):
            PlaybookPath(long_name)

    def test_immutability(self):
        """PlaybookPath should be immutable (frozen dataclass)."""
        path = PlaybookPath("test.yml")
        with pytest.raises(AttributeError):
            path.value = "other.yml"


class TestExtraVars:
    """Tests for ExtraVars value object."""

    def test_valid_extra_vars(self):
        """Valid extra vars should be accepted."""
        extra = ExtraVars(values={"input_dir": "/opt/input", "version": "1.0"})
        assert extra.to_dict() == {"input_dir": "/opt/input", "version": "1.0"}

    def test_empty_extra_vars(self):
        """Empty extra vars should be accepted."""
        extra = ExtraVars(values={})
        assert extra.to_dict() == {}

    def test_none_values_raises(self):
        """None values should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be None"):
            ExtraVars(values=None)

    def test_invalid_key_raises(self):
        """Key with invalid characters should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid extra var key"):
            ExtraVars(values={"invalid-key": "value"})

    def test_key_starting_with_number_raises(self):
        """Key starting with number should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid extra var key"):
            ExtraVars(values={"1invalid": "value"})

    def test_exceeds_max_keys(self):
        """Exceeding max keys should raise ValueError."""
        too_many = {f"key_{i}": f"val_{i}" for i in range(51)}
        with pytest.raises(ValueError, match="cannot exceed"):
            ExtraVars(values=too_many)

    def test_to_dict_returns_copy(self):
        """to_dict should return a copy, not the original."""
        original = {"key_one": "value"}
        extra = ExtraVars(values=original)
        result = extra.to_dict()
        result["new_key"] = "new_value"
        assert "new_key" not in extra.values

    def test_immutability(self):
        """ExtraVars should be immutable (frozen dataclass)."""
        extra = ExtraVars(values={"key": "val"})
        with pytest.raises(AttributeError):
            extra.values = {}


class TestExecutionTimeout:
    """Tests for ExecutionTimeout value object."""

    def test_valid_timeout(self):
        """Valid timeout should be accepted."""
        timeout = ExecutionTimeout(minutes=30)
        assert timeout.minutes == 30

    def test_default_timeout(self):
        """Default timeout should be 30 minutes."""
        timeout = ExecutionTimeout.default()
        assert timeout.minutes == 30

    def test_to_seconds(self):
        """to_seconds should convert correctly."""
        timeout = ExecutionTimeout(minutes=10)
        assert timeout.to_seconds() == 600

    def test_minimum_timeout(self):
        """Minimum timeout of 1 minute should be accepted."""
        timeout = ExecutionTimeout(minutes=1)
        assert timeout.minutes == 1

    def test_maximum_timeout(self):
        """Maximum timeout of 120 minutes should be accepted."""
        timeout = ExecutionTimeout(minutes=120)
        assert timeout.minutes == 120

    def test_below_minimum_raises(self):
        """Timeout below minimum should raise ValueError."""
        with pytest.raises(ValueError, match="must be between"):
            ExecutionTimeout(minutes=0)

    def test_above_maximum_raises(self):
        """Timeout above maximum should raise ValueError."""
        with pytest.raises(ValueError, match="must be between"):
            ExecutionTimeout(minutes=121)

    def test_negative_timeout_raises(self):
        """Negative timeout should raise ValueError."""
        with pytest.raises(ValueError, match="must be between"):
            ExecutionTimeout(minutes=-5)

    def test_str_representation(self):
        """String representation should include unit."""
        timeout = ExecutionTimeout(minutes=30)
        assert str(timeout) == "30m"

    def test_immutability(self):
        """ExecutionTimeout should be immutable (frozen dataclass)."""
        timeout = ExecutionTimeout(minutes=30)
        with pytest.raises(AttributeError):
            timeout.minutes = 60
