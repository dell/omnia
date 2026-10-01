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

"""Unit tests for the governed cadence configuration contract."""

import os
from unittest.mock import patch

import pytest

from cadence_manager import (
    DEFAULT_CADENCE_CATALOG_FILENAME,
    DEFAULT_CADENCE_INTERVAL_DAYS,
    DEFAULT_CADENCE_PLAYBOOK_NAME,
    _load_unified_config,
    load_cadence_config,
)


def _defaults():
    """Return the operational cadence defaults used by focused tests."""
    return {
        "enabled": False,
        "interval_days": DEFAULT_CADENCE_INTERVAL_DAYS,
        "sync_timeout_seconds": 3600,
        "sync_poll_interval_seconds": 10,
    }


class TestUnifiedConfigLoading:
    """Validate the project-scoped ``cadence`` input mapping."""

    @pytest.mark.unit
    def test_load_unified_config_success(self, temp_dir):
        """TC-UT-001-001: Load supported operator settings."""
        config_file = temp_dir / "build_stream_config.yml"
        config_file.write_text(
            """
cadence:
  enabled: true
  interval_days: 3
  sync_timeout_seconds: 1800
  sync_poll_interval_seconds: 5
""",
            encoding="utf-8",
        )

        result = _load_unified_config(str(config_file), _defaults())

        assert result["enabled"] is True
        assert result["interval_days"] == 3
        assert result["sync_timeout_seconds"] == 1800
        assert result["sync_poll_interval_seconds"] == 5

    @pytest.mark.unit
    def test_fixed_catalog_and_playbook_are_rejected(self, temp_dir):
        """TC-UT-001-002: Unknown cadence inputs match schema rejection."""
        config_file = temp_dir / "build_stream_config.yml"
        config_file.write_text(
            """
cadence:
  enabled: true
  interval_days: 1
  catalog_filename: other.json
  playbook_name: other.yml
""",
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="Unsupported cadence"):
            _load_unified_config(
                str(config_file),
                _defaults(),
                strict=True,
            )

    @pytest.mark.unit
    def test_interval_days_below_one_is_rejected(self, temp_dir):
        """TC-UT-001-003: Runtime matches the schema minimum of one day."""
        config_file = temp_dir / "build_stream_config.yml"
        config_file.write_text(
            "cadence:\n  enabled: true\n  interval_days: 0\n",
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="interval_days"):
            _load_unified_config(
                str(config_file),
                _defaults(),
                strict=True,
            )

    @pytest.mark.unit
    def test_legacy_seconds_falls_back_to_safe_defaults(self, temp_dir):
        """TC-UT-001-004: Removed cadence inputs cannot alter runtime state."""
        config_file = temp_dir / "build_stream_config.yml"
        config_file.write_text(
            """
enable_cadence_polling: true
cadence_polling_interval_seconds: 60
cadence:
  enabled: false
  interval_seconds: 60
  interval_days: 2
""",
            encoding="utf-8",
        )

        result = _load_unified_config(str(config_file), _defaults())

        assert result["enabled"] is False
        assert result["interval_days"] == DEFAULT_CADENCE_INTERVAL_DAYS
        assert "interval_seconds" not in result

    @pytest.mark.unit
    def test_non_strict_missing_file_returns_defaults(self, temp_dir):
        """TC-UT-001-005: Startup can use safe disabled defaults."""
        result = _load_unified_config(
            str(temp_dir / "missing.yml"),
            _defaults(),
        )

        assert result == _defaults()

    @pytest.mark.unit
    def test_strict_malformed_config_raises(self, temp_dir):
        """TC-UT-001-006: Reload detects malformed configuration."""
        config_file = temp_dir / "build_stream_config.yml"
        config_file.write_text("cadence: [invalid", encoding="utf-8")

        with pytest.raises(ValueError, match="Failed to load cadence"):
            _load_unified_config(
                str(config_file),
                _defaults(),
                strict=True,
            )

    @pytest.mark.unit
    def test_strict_missing_cadence_mapping_raises(self, temp_dir):
        """TC-UT-001-007: Reload cannot silently reset to defaults."""
        config_file = temp_dir / "build_stream_config.yml"
        config_file.write_text("enable_build_stream: true\n", encoding="utf-8")

        with pytest.raises(ValueError, match="Failed to load cadence"):
            _load_unified_config(
                str(config_file),
                _defaults(),
                strict=True,
            )

    @pytest.mark.parametrize(
        "field,value,error",
        [
            ("gitlab_host", 123, "gitlab_host"),
            ("gitlab_https_port", "443", "gitlab_https_port"),
            ("gitlab_https_port", 65536, "gitlab_https_port"),
            ("gitlab_project_name", "bad project", "gitlab_project_name"),
            ("gitlab_default_branch", "", "gitlab_default_branch"),
        ],
    )
    @pytest.mark.unit
    def test_strict_gitlab_fields_match_schema_types(
        self,
        temp_dir,
        field,
        value,
        error,
    ):
        """TC-UT-001-012: Reload rejects invalid root GitLab fields."""
        config_file = temp_dir / "build_stream_config.yml"
        config_file.write_text(
            "cadence:\n  enabled: true\n  interval_days: 1\n",
            encoding="utf-8",
        )
        with config_file.open("a", encoding="utf-8") as config_stream:
            config_stream.write(f"{field}: {value!r}\n")

        with pytest.raises(ValueError, match=error):
            _load_unified_config(
                str(config_file),
                _defaults(),
                strict=True,
            )


class TestConfigLoadingResolution:
    """Validate startup and reload path resolution."""

    @pytest.mark.unit
    def test_load_config_from_explicit_path(self, temp_dir):
        """TC-UT-001-008: Load the explicitly selected project config."""
        config_file = temp_dir / "build_stream_config.yml"
        config_file.write_text(
            "cadence:\n  enabled: true\n  interval_days: 4\n",
            encoding="utf-8",
        )

        result = load_cadence_config(str(config_file))

        assert result["enabled"] is True
        assert result["interval_days"] == 4

    @pytest.mark.unit
    def test_load_config_defaults_when_missing(self, temp_dir):
        """TC-UT-001-009: Missing startup config keeps cadence disabled."""
        with patch.dict(
            os.environ,
            {"OMNIA_DATA_PATH": str(temp_dir)},
            clear=False,
        ):
            result = load_cadence_config()

        assert result["enabled"] is False
        assert result["interval_days"] == DEFAULT_CADENCE_INTERVAL_DAYS
        assert DEFAULT_CADENCE_CATALOG_FILENAME == "cadence_catalog_rhel.json"
        assert DEFAULT_CADENCE_PLAYBOOK_NAME == "repo_sync.yml"

    @pytest.mark.unit
    def test_strict_missing_config_raises(self, temp_dir):
        """TC-UT-001-010: Reload preserves state when its file disappears."""
        with pytest.raises(ValueError, match="does not exist"):
            load_cadence_config(
                str(temp_dir / "missing.yml"),
                strict=True,
            )

    @pytest.mark.unit
    def test_load_config_env_var_override(self, temp_dir):
        """TC-UT-001-011: BUILD_STREAM_CONFIG_PATH remains supported."""
        config_file = temp_dir / "custom_config.yml"
        config_file.write_text(
            "cadence:\n  enabled: true\n  interval_days: 5\n",
            encoding="utf-8",
        )

        with patch.dict(
            os.environ,
            {"BUILD_STREAM_CONFIG_PATH": str(config_file)},
            clear=False,
        ):
            result = load_cadence_config()

        assert result["enabled"] is True
        assert result["interval_days"] == 5

    @pytest.mark.unit
    def test_malformed_credentials_raise_in_strict_reload(self, temp_dir):
        """TC-UT-001-013: Malformed credential YAML cannot escape reload."""
        config_file = temp_dir / "build_stream_config.yml"
        credentials_file = temp_dir / "build_stream_credentials.yml"
        config_file.write_text(
            "cadence:\n  enabled: true\n  interval_days: 1\n",
            encoding="utf-8",
        )
        credentials_file.write_text("gitlab_root_token: [broken", encoding="utf-8")

        with pytest.raises(ValueError, match="GitLab credentials"):
            load_cadence_config(
                str(config_file),
                str(credentials_file),
                strict=True,
            )
