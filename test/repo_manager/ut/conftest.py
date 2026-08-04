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
"""Pytest fixtures for repo_manager unit tests."""

import json
import pathlib

import pytest
import yaml


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent
SRC_DIR = REPO_ROOT / "src"
INPUT_DIR = SRC_DIR / "repo_manager" / "input" / "project_default"
SCHEMA_DIR = (
    SRC_DIR
    / "repo_manager"
    / "plugins"
    / "module_utils"
    / "input_validation"
    / "schema"
)


@pytest.fixture
def repo_root():
    """Return the repository root path."""
    return REPO_ROOT


@pytest.fixture
def src_dir():
    """Return the src/ directory path."""
    return SRC_DIR


@pytest.fixture
def input_dir():
    """Return the repo_manager input/project_default/ directory path."""
    return INPUT_DIR


@pytest.fixture
def schema_dir():
    """Return the schema directory path."""
    return SCHEMA_DIR


@pytest.fixture
def repo_manager_config(input_dir):
    """Load and return repo_manager_config.yml as a dict."""
    config_file = input_dir / "repo_manager_config.yml"
    assert config_file.exists(), f"repo_manager_config.yml not found at {config_file}"
    with open(config_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def software_config(input_dir):
    """Load and return software_config.json as a dict."""
    config_file = input_dir / "software_config.json"
    assert config_file.exists(), f"software_config.json not found at {config_file}"
    with open(config_file, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def endpoint_config(input_dir):
    """Load and return repo_manager_endpoint_config.yml as a dict."""
    config_file = input_dir / "repo_manager_endpoint_config.yml"
    assert config_file.exists(), (
        f"repo_manager_endpoint_config.yml not found at {config_file}"
    )
    with open(config_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def software_config_schema(schema_dir):
    """Load and return the software_config.json JSON schema."""
    schema_file = schema_dir / "software_config.json"
    assert schema_file.exists(), f"Schema not found at {schema_file}"
    with open(schema_file, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def endpoint_config_schema(schema_dir):
    """Load and return the repo_manager_endpoint_config.json JSON schema."""
    schema_file = schema_dir / "repo_manager_endpoint_config.json"
    assert schema_file.exists(), f"Schema not found at {schema_file}"
    with open(schema_file, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def repo_manager_config_schema(schema_dir):
    """Load and return the repo_manager_config.json JSON schema."""
    schema_file = schema_dir / "repo_manager_config.json"
    assert schema_file.exists(), f"Schema not found at {schema_file}"
    with open(schema_file, "r", encoding="utf-8") as f:
        return json.load(f)
