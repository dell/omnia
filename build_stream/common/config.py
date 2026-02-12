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
from dataclasses import dataclass
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
class FileStoreConfig:
    """File store configuration."""
    base_path: str


@dataclass
class BuildStreamConfig:
    """BuildStream configuration."""
    artifact_store: ArtifactStoreConfig
    file_store: Optional[FileStoreConfig]


def load_config(config_path: Optional[str] = None) -> BuildStreamConfig:
    """Load BuildStream configuration from INI file.
    
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
        config_path = os.getenv(
            "BUILD_STREAM_CONFIG_PATH",
            "/opt/omnia/windsurf/build_stream_venu_oim/build_stream/build_stream.ini"
        )
    
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")
    
    parser = configparser.ConfigParser()
    parser.read(config_file)
    
    if not parser.sections():
        raise ValueError(f"Empty configuration file: {config_file}")
    
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
        working_dir=parser.get(artifact_store_section, "working_dir", fallback="/tmp/build_stream"),
        max_file_size_bytes=max_file_size_bytes,
        max_archive_uncompressed_bytes=max_archive_uncompressed_bytes,
        max_archive_entries=max_archive_entries,
    )
    
    # Parse file_store config only if backend is file_store
    file_store = None
    if backend == "file_store":
        if parser.has_section("file_store") and parser.has_option("file_store", "base_path"):
            file_store = FileStoreConfig(
                base_path=parser.get("file_store", "base_path")
            )
        else:
            raise ValueError("file_store section with base_path is required when backend=file_store")
    
    return BuildStreamConfig(
        artifact_store=artifact_store,
        file_store=file_store,
    )
