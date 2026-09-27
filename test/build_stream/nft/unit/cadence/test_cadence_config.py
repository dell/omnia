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

"""
Unit tests for cadence configuration loading (UT-001).
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from cadence_manager import (
    load_cadence_config,
    _validate_catalog_filename,
    _load_unified_config,
)


class TestCatalogFilenameValidation:
    """UT-002: Catalog filename validation tests."""

    def test_validate_safe_filename(self):
        """TC-UT-002-001: Validate safe catalog filename."""
        assert _validate_catalog_filename("cadence_catalog_rhel.json") is True
        assert _validate_catalog_filename("catalog.json") is True
        assert _validate_catalog_filename("my-catalog_v2.json") is True

    def test_reject_path_traversal(self):
        """TC-UT-002-002: Reject path traversal attempts."""
        assert _validate_catalog_filename("../../../etc/passwd") is False
        assert _validate_catalog_filename("../config.json") is False
        assert _validate_catalog_filename("../../catalog.json") is False

    def test_reject_slashes(self):
        """TC-UT-002-003: Reject filenames with slashes."""
        assert _validate_catalog_filename("subdir/catalog.json") is False
        assert _validate_catalog_filename("/etc/catalog.json") is False
        assert _validate_catalog_filename("C:\\Windows\\catalog.json") is False

    def test_reject_non_json(self):
        """TC-UT-002-004: Reject non-JSON filenames."""
        assert _validate_catalog_filename("catalog.txt") is False
        assert _validate_catalog_filename("catalog.yml") is False
        assert _validate_catalog_filename("catalog") is False

    def test_reject_empty_filename(self):
        """TC-UT-002-005: Reject empty filename."""
        assert _validate_catalog_filename("") is False
        assert _validate_catalog_filename(None) is False


class TestUnifiedConfigLoading:
    """UT-001-001: Load config from the cadence group of build_stream_config.yml."""

    def test_load_unified_config_success(self, temp_dir, sample_cadence_config):
        """TC-UT-001-001: Load unified config from build_stream_config.yml."""
        config_file = temp_dir / "build_stream_config.yml"
        config_file.write_text("""
cadence:
  enabled: true
  interval_seconds: 43200
  catalog_filename: "cadence_catalog_rhel.json"
  gitlab_repo_path: "/tmp/test_repo"
  playbook_name: "repo_sync.yml"
  sync_timeout_seconds: 1800
  sync_poll_interval_seconds: 5
""")

        defaults = {"enabled": False, "interval_seconds": 86400}
        result = _load_unified_config(str(config_file), defaults)

        assert result["enabled"] is True
        assert result["interval_seconds"] == 43200
        assert result["catalog_filename"] == "cadence_catalog_rhel.json"
        assert result["gitlab_repo_path"] == "/tmp/test_repo"  # nosec B108
        assert result["playbook_name"] == "repo_sync.yml"
        assert result["sync_timeout_seconds"] == 1800
        assert result["sync_poll_interval_seconds"] == 5

    def test_load_unified_config_partial(self, temp_dir):
        """TC-UT-001-006: Merge partial config with defaults."""
        config_file = temp_dir / "build_stream_config.yml"
        config_file.write_text("""
cadence:
  enabled: true
  interval_seconds: 7200
""")

        defaults = {
            "enabled": False,
            "interval_seconds": 86400,
            "catalog_filename": "cadence_catalog_rhel.json",
            "gitlab_repo_path": "",
            "playbook_name": "repo_sync.yml",
            "sync_timeout_seconds": 3600,
            "sync_poll_interval_seconds": 10,
        }
        result = _load_unified_config(str(config_file), defaults)

        assert result["enabled"] is True
        assert result["interval_seconds"] == 7200
        assert result["catalog_filename"] == "cadence_catalog_rhel.json"  # Default
        assert result["playbook_name"] == "repo_sync.yml"  # Default

    def test_load_unified_config_invalid_interval(self, temp_dir):
        """TC-UT-001-005: Enforce minimum polling interval (3600 seconds)."""
        config_file = temp_dir / "build_stream_config.yml"
        config_file.write_text("""
cadence:
  enabled: true
  interval_seconds: 1800
  catalog_filename: "cadence_catalog_rhel.json"
""")

        defaults = {
            "enabled": False,
            "interval_seconds": 86400,
            "catalog_filename": "cadence_catalog_rhel.json"
        }
        result = _load_unified_config(str(config_file), defaults)

        assert result["interval_seconds"] == 3600  # Minimum enforced

    def test_load_unified_config_invalid_filename(self, temp_dir):
        """TC-UT-001-004: Validate catalog filename pattern."""
        config_file = temp_dir / "build_stream_config.yml"
        config_file.write_text("""
cadence:
  enabled: true
  catalog_filename: "../../../etc/passwd"
  interval_seconds: 86400
""")

        defaults = {
            "enabled": False,
            "catalog_filename": "cadence_catalog_rhel.json",
            "interval_seconds": 86400
        }

        # An invalid filename aborts the load; defaults are returned untouched
        result = _load_unified_config(str(config_file), defaults)
        assert result == defaults
        assert result["catalog_filename"] == "cadence_catalog_rhel.json"

    def test_load_unified_config_missing_file(self, temp_dir):
        """TC-UT-001-003: Handle missing config file."""
        config_file = temp_dir / "nonexistent.yml"
        defaults = {"enabled": False, "interval_seconds": 86400}
        
        result = _load_unified_config(str(config_file), defaults)
        assert result == defaults


    def test_load_unified_config_no_cadence_group(self, temp_dir):
        """TC-UT-001-007: Fall back to defaults when the cadence group is absent."""
        config_file = temp_dir / "build_stream_config.yml"
        config_file.write_text("""
enable_build_stream: true
gitlab_host: "10.0.0.1"
""")

        defaults = {
            "enabled": False,
            "interval_seconds": 86400,
            "catalog_filename": "cadence_catalog_rhel.json",
        }
        result = _load_unified_config(str(config_file), defaults)
        assert result == defaults

    def test_load_unified_config_ignores_top_level_keys(self, temp_dir):
        """TC-UT-001-008: Cadence keys outside the cadence group are ignored."""
        config_file = temp_dir / "build_stream_config.yml"
        config_file.write_text("""
enable_cadence_polling: true
cadence_polling_interval_seconds: 43200
cadence:
  enabled: false
  interval_seconds: 7200
""")

        defaults = {
            "enabled": False,
            "interval_seconds": 86400,
            "catalog_filename": "cadence_catalog_rhel.json",
        }
        result = _load_unified_config(str(config_file), defaults)

        assert result["enabled"] is False
        assert result["interval_seconds"] == 7200


class TestConfigLoadingPriority:
    """UT-001-001 through UT-001-003: Configuration loading resolution."""

    def test_load_config_from_explicit_path(self, temp_dir, mock_log_secure_info):
        """TC-UT-001-001: Load cadence group from an explicit config path."""
        unified_file = temp_dir / "build_stream_config.yml"
        unified_file.write_text("""
cadence:
  enabled: true
  interval_seconds: 43200
""")

        with patch.dict(os.environ, {"OMNIA_DATA_PATH": str(temp_dir)}):
            result = load_cadence_config(str(unified_file))

        assert result["enabled"] is True
        assert result["interval_seconds"] == 43200

    def test_load_config_defaults_when_missing(self, temp_dir, mock_log_secure_info):
        """TC-UT-001-003: Use defaults when no config file exists."""
        with patch.dict(os.environ, {"OMNIA_DATA_PATH": str(temp_dir)}):
            result = load_cadence_config()

        assert result["enabled"] is False
        assert result["interval_seconds"] == 86400
        assert result["catalog_filename"] == "cadence_catalog_rhel.json"

    def test_load_config_env_var_override(self, temp_dir, mock_log_secure_info):
        """TC-UT-001-001: BUILD_STREAM_CONFIG_PATH env var override."""
        custom_file = temp_dir / "custom_config.yml"
        custom_file.write_text("""
cadence:
  enabled: true
  interval_seconds: 10800
""")

        with patch.dict(os.environ, {"BUILD_STREAM_CONFIG_PATH": str(custom_file)}):
            result = load_cadence_config()

        assert result["enabled"] is True
        assert result["interval_seconds"] == 10800
