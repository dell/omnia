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

"""Automatic image cleanup (retention) configuration (ER-BSM-002 Story 4).

Values come from the ``retention`` group of the project-scoped
``build_stream_config.yml``. The file is read on every call, so a changed
value applies to the next cleanup cycle without restarting the container.
"""

import os
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from api.logging_utils import log_secure_info

DEFAULT_AUTO_CLEANUP_ENABLED = True
DEFAULT_RETENTION_AGE_DAYS = 90
DEFAULT_MIN_KEEP_COUNT = 5
DEFAULT_EVALUATION_INTERVAL_HOURS = 24

# Minimum accepted value for each integer setting (mirrors the JSON schema).
_INT_MINIMUMS = {
    "retention_age_days": 1,
    "min_keep_count": 0,
    "evaluation_interval_hours": 1,
}


@dataclass(frozen=True)
class RetentionConfig:
    """Effective automatic cleanup settings."""

    auto_cleanup_enabled: bool = DEFAULT_AUTO_CLEANUP_ENABLED
    retention_age_days: int = DEFAULT_RETENTION_AGE_DAYS
    min_keep_count: int = DEFAULT_MIN_KEEP_COUNT
    evaluation_interval_hours: int = DEFAULT_EVALUATION_INTERVAL_HOURS

    def as_dict(self) -> Dict[str, Any]:
        """Return the settings as a plain dictionary."""
        return {item.name: getattr(self, item.name) for item in fields(self)}


def build_stream_config_path() -> Path:
    """Return the project-scoped ``build_stream_config.yml`` path."""
    omnia_data_path = Path(os.getenv("OMNIA_DATA_PATH", "/opt/omnia"))
    project_name = os.getenv("OMNIA_PROJECT_NAME", "project_default")
    return (
        omnia_data_path / "build_stream" / "input" / project_name
        / "build_stream_config.yml"
    )


def _invalid(key: str, value: Any) -> ValueError:
    return ValueError(f"Invalid retention.{key} value: {value!r}")


def _parse_section(section: Dict[str, Any]) -> RetentionConfig:
    """Validate a ``retention`` mapping; missing keys keep built-in defaults.

    Raises:
        ValueError: If any present value has the wrong type or is out of range.
    """
    unknown = set(section) - {item.name for item in fields(RetentionConfig)}
    if unknown:
        raise ValueError(f"Unknown retention keys: {sorted(unknown)}")

    values = RetentionConfig().as_dict()
    enabled = section.get("auto_cleanup_enabled", values["auto_cleanup_enabled"])
    if not isinstance(enabled, bool):
        raise _invalid("auto_cleanup_enabled", enabled)
    values["auto_cleanup_enabled"] = enabled

    for key, minimum in _INT_MINIMUMS.items():
        value = section.get(key, values[key])
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            raise _invalid(key, value)
        values[key] = value

    return RetentionConfig(**values)


def load_retention_config(
    config_path: Optional[Path] = None,
    fallback: Optional[RetentionConfig] = None,
) -> RetentionConfig:
    """Load the ``retention`` settings from ``build_stream_config.yml``.

    A missing file or missing ``retention`` group yields built-in defaults.
    An unreadable file or an invalid value yields *fallback* (the last
    known-good configuration when called by the scheduler), so a typo never
    silently shortens the retention window to the default.

    Args:
        config_path: Override path to ``build_stream_config.yml``.
        fallback: Configuration returned when the file cannot be used.

    Returns:
        Effective retention configuration.
    """
    fallback = fallback or RetentionConfig()
    path = config_path or build_stream_config_path()

    try:
        if not path.exists():
            return RetentionConfig()
        with open(path, encoding="utf-8") as config_file:
            raw = yaml.safe_load(config_file) or {}
        if not isinstance(raw, dict):
            raise ValueError("build_stream_config.yml is not a mapping")
        section = raw.get("retention")
        if section is None:
            return RetentionConfig()
        if not isinstance(section, dict):
            raise ValueError("retention group is not a mapping")
        return _parse_section(section)
    except (OSError, ValueError, TypeError, yaml.YAMLError) as exc:
        log_secure_info(
            "warning",
            f"Retention config not applied ({exc}); keeping "
            f"{fallback.as_dict()}",
        )
        return fallback
