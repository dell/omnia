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
"""Pytest fixtures for image_build_manager tests."""

import os
import pathlib

import pytest
import yaml


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SRC_DIR = REPO_ROOT / "src"
INPUT_DIR = SRC_DIR / "input" / "project_default"
REPO_MGR_OUTPUT = INPUT_DIR / "repo_manager_output"


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
    """Return the input/project_default/ directory path."""
    return INPUT_DIR


@pytest.fixture
def repo_manager_output():
    """Return the repo_manager_output/ directory path."""
    return REPO_MGR_OUTPUT


@pytest.fixture
def functional_group_packages(repo_manager_output):
    """Load and return functional_group_packages.yml as a dict."""
    pkg_file = repo_manager_output / "functional_group_packages.yml"
    assert pkg_file.exists(), f"functional_group_packages.yml not found at {pkg_file}"
    with open(pkg_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def image_build_config(input_dir):
    """Load and return image_build_config.yml as a dict."""
    config_file = input_dir / "image_build_config.yml"
    assert config_file.exists(), f"image_build_config.yml not found at {config_file}"
    with open(config_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture
def repo_status(repo_manager_output):
    """Load and return repo_status.yml as a dict."""
    status_file = repo_manager_output / "repo_status.yml"
    assert status_file.exists(), f"repo_status.yml not found at {status_file}"
    with open(status_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
