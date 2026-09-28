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
"""Pytest fixtures for discovery unit tests."""

import pathlib

import pytest
import yaml


# ut/conftest.py -> ut/ -> discovery/ -> test/ -> omnia/
REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC_DIR = REPO_ROOT / "src" / "discovery"
INPUT_DIR = SRC_DIR / "input"
SCHEMA_DIR = (
    SRC_DIR
    / "plugins" / "module_utils" / "discovery_validation" / "schema"
)


@pytest.fixture
def repo_root():
    """Return the repository root path."""
    return REPO_ROOT


@pytest.fixture
def src_dir():
    """Return the src/discovery directory path."""
    return SRC_DIR


@pytest.fixture
def input_dir():
    """Return the input/ directory path."""
    return INPUT_DIR


@pytest.fixture
def schema_dir():
    """Return the schema/ directory path."""
    return SCHEMA_DIR


@pytest.fixture
def discovery_config(input_dir):
    """Load and return discovery_config.yml as a dict."""
    config_file = input_dir / "discovery_config.yml"
    assert config_file.exists(), f"discovery_config.yml not found at {config_file}"
    with open(config_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def network_spec(input_dir):
    """Load and return network_spec.yml as a dict."""
    spec_file = input_dir / "network_spec.yml"
    assert spec_file.exists(), f"network_spec.yml not found at {spec_file}"
    with open(spec_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
