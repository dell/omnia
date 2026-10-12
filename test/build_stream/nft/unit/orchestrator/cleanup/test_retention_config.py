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

"""Unit tests for the retention (automatic cleanup) configuration loader."""

from pathlib import Path

import pytest
import yaml

from orchestrator.cleanup.retention_config import (
    DEFAULT_EVALUATION_INTERVAL_HOURS,
    DEFAULT_MIN_KEEP_COUNT,
    DEFAULT_RETENTION_AGE_DAYS,
    RetentionConfig,
    build_stream_config_path,
    load_retention_config,
)

pytestmark = pytest.mark.unit

SHIPPED_CONFIG = (
    Path(__file__).parents[6] / "src" / "build_stream" / "input"
    / "build_stream_config.yml"
)


def _write(path: Path, data) -> Path:
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_missing_file_returns_defaults(tmp_path):
    """A missing config file yields the built-in defaults."""
    config = load_retention_config(tmp_path / "absent.yml")

    assert config == RetentionConfig()
    assert config.retention_age_days == DEFAULT_RETENTION_AGE_DAYS == 90
    assert config.min_keep_count == DEFAULT_MIN_KEEP_COUNT
    assert config.evaluation_interval_hours == DEFAULT_EVALUATION_INTERVAL_HOURS
    assert config.auto_cleanup_enabled is True


def test_missing_retention_group_returns_defaults(tmp_path):
    """A config without a retention group yields defaults."""
    path = _write(tmp_path / "c.yml", {"cadence": {"enabled": True}})

    assert load_retention_config(path) == RetentionConfig()


def test_values_are_read_from_config(tmp_path):
    """Every retention key is read from build_stream_config.yml."""
    path = _write(tmp_path / "c.yml", {"retention": {
        "auto_cleanup_enabled": False,
        "retention_age_days": 30,
        "min_keep_count": 0,
        "evaluation_interval_hours": 6,
    }})

    config = load_retention_config(path)

    assert config == RetentionConfig(
        auto_cleanup_enabled=False,
        retention_age_days=30,
        min_keep_count=0,
        evaluation_interval_hours=6,
    )


def test_partial_group_fills_missing_keys_with_defaults(tmp_path):
    """Keys absent from the retention group keep the defaults."""
    path = _write(tmp_path / "c.yml", {"retention": {"retention_age_days": 120}})

    config = load_retention_config(path)

    assert config.retention_age_days == 120
    assert config.min_keep_count == DEFAULT_MIN_KEEP_COUNT


@pytest.mark.parametrize("section", [
    {"retention_age_days": 0},
    {"retention_age_days": "90"},
    {"retention_age_days": True},
    {"min_keep_count": -1},
    {"evaluation_interval_hours": 0},
    {"auto_cleanup_enabled": "yes"},
    {"unknown_key": 1},
])
def test_invalid_values_keep_fallback(tmp_path, section):
    """An invalid value never silently replaces the last good settings."""
    path = _write(tmp_path / "c.yml", {"retention": section})
    last_good = RetentionConfig(retention_age_days=365)

    assert load_retention_config(path, fallback=last_good) == last_good


def test_unparsable_yaml_keeps_fallback(tmp_path):
    """Malformed YAML keeps the fallback configuration."""
    path = tmp_path / "c.yml"
    path.write_text("retention: [unclosed", encoding="utf-8")
    last_good = RetentionConfig(min_keep_count=9)

    assert load_retention_config(path, fallback=last_good) == last_good


def test_non_mapping_retention_group_keeps_fallback(tmp_path):
    """A non-mapping retention group is rejected."""
    path = _write(tmp_path / "c.yml", {"retention": [1, 2]})
    last_good = RetentionConfig(evaluation_interval_hours=2)

    assert load_retention_config(path, fallback=last_good) == last_good


def test_default_path_is_project_scoped(monkeypatch):
    """The default path follows OMNIA_DATA_PATH and OMNIA_PROJECT_NAME."""
    monkeypatch.setenv("OMNIA_DATA_PATH", "/data")
    monkeypatch.setenv("OMNIA_PROJECT_NAME", "proj")

    assert build_stream_config_path() == Path(
        "/data/build_stream/input/proj/build_stream_config.yml"
    )


def test_shipped_config_declares_default_retention():
    """The shipped build_stream_config.yml exposes the 90-day default."""
    config = load_retention_config(SHIPPED_CONFIG, fallback=RetentionConfig(1))

    assert config == RetentionConfig()
