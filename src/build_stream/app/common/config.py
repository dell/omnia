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

"""Configuration loader for BuildStream."""

import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import configparser


@dataclass
class ArtifactStoreConfig:
    """Artifact store configuration."""
    backend: str
    working_dir: str
    max_file_size_bytes: int
    max_archive_uncompressed_bytes: int
    max_archive_entries: int


@dataclass
class PathsConfig:
    """BuildStream paths configuration."""
    build_stream_base_path: str


@dataclass
class FileStoreConfig:
    """File store configuration."""
    base_path: str


MAX_LOG_TAIL_LINES_LIMIT = 10000
MIN_LOG_RESPONSE_BYTES = 1024
MAX_LOG_RESPONSE_BYTES_LIMIT = 50 * 1024 * 1024


def default_log_root() -> str:
    """Return the container path of the published job log directory."""
    return _expand_env("${OMNIA_DATA_PATH}/build_stream/log")


@dataclass
class LogQueryConfig:  # pylint: disable=too-many-instance-attributes
    """Pipeline log query API configuration (ER-BSM-003)."""
    log_root: str = field(default_factory=default_log_root)
    default_tail_lines: int = 50
    max_tail_lines: int = MAX_LOG_TAIL_LINES_LIMIT
    max_response_bytes: int = 10 * 1024 * 1024
    rate_limit_per_minute: int = 60
    max_concurrent: int = 5

    def __post_init__(self) -> None:
        """Validate bounds so a bad INI value cannot disable a safety limit."""
        if not 1 <= self.max_tail_lines <= MAX_LOG_TAIL_LINES_LIMIT:
            raise ValueError(
                f"log_query.max_tail_lines must be between 1 and {MAX_LOG_TAIL_LINES_LIMIT}"
            )
        if not 1 <= self.default_tail_lines <= self.max_tail_lines:
            raise ValueError("log_query.default_tail_lines must be between 1 and max_tail_lines")
        if not MIN_LOG_RESPONSE_BYTES <= self.max_response_bytes <= MAX_LOG_RESPONSE_BYTES_LIMIT:
            raise ValueError(
                f"log_query.max_response_bytes must be between {MIN_LOG_RESPONSE_BYTES} "
                f"and {MAX_LOG_RESPONSE_BYTES_LIMIT}"
            )
        if self.rate_limit_per_minute < 1:
            raise ValueError("log_query.rate_limit_per_minute must be >= 1")
        if self.max_concurrent < 1:
            raise ValueError("log_query.max_concurrent must be >= 1")
        if not os.path.isabs(self.log_root):
            raise ValueError("log_query.log_root must be an absolute path")


@dataclass
class BuildStreamConfig:
    """BuildStream configuration."""
    paths: PathsConfig
    artifact_store: ArtifactStoreConfig
    file_store: Optional[FileStoreConfig]
    log_query: LogQueryConfig = field(default_factory=LogQueryConfig)


def _expand_env(value: str) -> str:
    """Expand ``${VAR}`` and ``$VAR`` references in *value* using ``os.environ``.

    This lets ``build_stream.ini`` use placeholders such as
    ``${OMNIA_DATA_PATH}/build_stream_root`` so paths are not hardcoded.

    If ``OMNIA_DATA_PATH`` is not already in the environment it is
    temporarily injected with the standard default so that expansion
    never produces a literal ``${OMNIA_DATA_PATH}`` in output paths.
    """
    os.environ.setdefault("OMNIA_DATA_PATH", "/opt/omnia")
    return os.path.expandvars(value)


# Default path to build_stream.ini when BUILD_STREAM_CONFIG_PATH is not set.
# The container always sets the env var; this fallback is for local dev only.
_DEFAULT_INI_PATH = os.path.join(
    os.getenv("OMNIA_DATA_PATH", "/opt/omnia"),
    "build_stream", "build_stream.ini",
)

# Default base path derived from environment (used as fallback)
_DEFAULT_BUILD_STREAM_ROOT = os.path.join(
    os.getenv("OMNIA_DATA_PATH", "/opt/omnia"), "build_stream_root"
)


def load_config(config_path: Optional[str] = None) -> BuildStreamConfig:
    """Load BuildStream configuration from INI file.

    INI values may contain ``${VAR}`` references that are expanded from
    the process environment (e.g. ``${OMNIA_DATA_PATH}``).

    Args:
        config_path: Path to configuration file. If None, uses BUILD_STREAM_CONFIG_PATH
                    environment variable or default path.

    Returns:
        BuildStreamConfig instance.

    Raises:
        FileNotFoundError: If config file not found.
        ValueError: If config is invalid.
    """
    if config_path is None:
        config_path = os.getenv("BUILD_STREAM_CONFIG_PATH", _DEFAULT_INI_PATH)

    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")

    parser = configparser.ConfigParser()
    parser.read(config_file)

    if not parser.sections():
        raise ValueError(f"Empty configuration file: {config_file}")

    # Parse paths config
    paths_section = "paths"
    build_stream_base_path = _expand_env(
        parser.get(paths_section, "build_stream_base_path",
                   fallback=_DEFAULT_BUILD_STREAM_ROOT)
    )

    paths = PathsConfig(
        build_stream_base_path=build_stream_base_path,
    )

    # Parse artifact_store config
    artifact_store_section = "artifact_store"
    backend = parser.get(artifact_store_section, "backend", fallback="file_store")

    # Parse optional size limits with defaults
    max_file_size_bytes = 5242880  # 5MB default
    max_archive_uncompressed_bytes = 52428800  # 50MB default
    max_archive_entries = 500  # default

    if parser.has_option(artifact_store_section, "max_file_size_bytes"):
        max_file_size_bytes = parser.getint(artifact_store_section, "max_file_size_bytes")

    if parser.has_option(artifact_store_section, "max_archive_uncompressed_bytes"):
        max_archive_uncompressed_bytes = parser.getint(artifact_store_section, "max_archive_uncompressed_bytes")

    if parser.has_option(artifact_store_section, "max_archive_entries"):
        max_archive_entries = parser.getint(artifact_store_section, "max_archive_entries")

    artifact_store = ArtifactStoreConfig(
        backend=backend,
        working_dir=parser.get(
            artifact_store_section,
            "working_dir",
            fallback=f"{tempfile.gettempdir()}/build_stream",
        ),
        max_file_size_bytes=max_file_size_bytes,
        max_archive_uncompressed_bytes=max_archive_uncompressed_bytes,
        max_archive_entries=max_archive_entries,
    )

    # Parse file_store config only if backend is file_store
    file_store = None
    if backend == "file_store":
        if parser.has_section("file_store") and parser.has_option("file_store", "base_path"):
            file_store = FileStoreConfig(
                base_path=_expand_env(parser.get("file_store", "base_path"))
            )
        else:
            raise ValueError("file_store section with base_path is required when backend=file_store")

    return BuildStreamConfig(
        paths=paths,
        artifact_store=artifact_store,
        file_store=file_store,
        log_query=_load_log_query_config(parser),
    )


def _load_log_query_config(parser: configparser.ConfigParser) -> LogQueryConfig:
    """Parse the optional ``[log_query]`` section, falling back to defaults."""
    section = "log_query"
    defaults = LogQueryConfig()
    if not parser.has_section(section):
        return defaults
    return LogQueryConfig(
        log_root=_expand_env(parser.get(section, "log_root", fallback=defaults.log_root)),
        default_tail_lines=parser.getint(
            section, "default_tail_lines", fallback=defaults.default_tail_lines
        ),
        max_tail_lines=parser.getint(section, "max_tail_lines", fallback=defaults.max_tail_lines),
        max_response_bytes=parser.getint(
            section, "max_response_bytes", fallback=defaults.max_response_bytes
        ),
        rate_limit_per_minute=parser.getint(
            section, "rate_limit_per_minute", fallback=defaults.rate_limit_per_minute
        ),
        max_concurrent=parser.getint(section, "max_concurrent", fallback=defaults.max_concurrent),
    )
