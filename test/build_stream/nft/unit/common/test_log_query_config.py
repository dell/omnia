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

"""[log_query] section of build_stream.ini (ER-BSM-003)."""

from dataclasses import asdict
from pathlib import Path

import pytest

from common.config import LogQueryConfig, load_config

pytestmark = pytest.mark.unit

BASE_INI = """
[paths]
build_stream_base_path = ${OMNIA_DATA_PATH}/build_stream_root

[artifact_store]
backend = file_store

[file_store]
base_path = ${OMNIA_DATA_PATH}/build_stream_root/artifacts
"""

REPO_INI = Path(__file__).resolve().parents[5] / "src" / "build_stream" / "app" / "build_stream.ini"


def _write(tmp_path, extra: str = "") -> str:
    """Write an INI file and return its path."""
    path = tmp_path / "build_stream.ini"
    path.write_text(BASE_INI + extra, encoding="utf-8")
    return str(path)


class TestLogQueryConfig:
    """Defaults, overrides, and validation."""

    def test_missing_section_uses_defaults(self, tmp_path, monkeypatch):
        """GIVEN no [log_query] section THEN built-in defaults apply."""
        monkeypatch.setenv("OMNIA_DATA_PATH", "/data")
        config = load_config(_write(tmp_path)).log_query
        assert asdict(config) == asdict(LogQueryConfig(log_root="/data/build_stream/log"))

    def test_overrides_and_env_expansion(self, tmp_path, monkeypatch):
        """GIVEN explicit values THEN they are parsed and ${VAR} is expanded."""
        monkeypatch.setenv("OMNIA_DATA_PATH", "/data")
        config = load_config(_write(tmp_path, (
            "[log_query]\nlog_root = ${OMNIA_DATA_PATH}/logs\ndefault_tail_lines = 25\n"
            "max_tail_lines = 500\nmax_response_bytes = 2048\n"
            "rate_limit_per_minute = 10\nmax_concurrent = 2\n"
        ))).log_query
        assert config.log_root == "/data/logs"
        assert (config.default_tail_lines, config.max_tail_lines) == (25, 500)
        assert config.max_response_bytes == 2048
        assert (config.rate_limit_per_minute, config.max_concurrent) == (10, 2)

    @pytest.mark.parametrize(
        "line",
        [
            "max_tail_lines = 20000",
            "default_tail_lines = 0",
            "max_response_bytes = 10",
            "rate_limit_per_minute = 0",
            "max_concurrent = 0",
            "log_root = relative/path",
        ],
    )
    def test_invalid_values_rejected(self, tmp_path, line):
        """GIVEN an unsafe value THEN loading fails instead of disabling a limit."""
        with pytest.raises(ValueError):
            load_config(_write(tmp_path, f"[log_query]\n{line}\n"))

    def test_repository_ini_matches_defaults(self, monkeypatch):
        """The shipped build_stream.ini documents exactly the built-in defaults."""
        monkeypatch.setenv("OMNIA_DATA_PATH", "/opt/omnia")
        assert asdict(load_config(str(REPO_INI)).log_query) == asdict(LogQueryConfig())
