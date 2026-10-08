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
"""Pytest fixtures for utils unit tests."""

import pathlib

import pytest

# ut/conftest.py -> ut/ -> utils/ -> test/ -> omnia/
REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC_DIR = REPO_ROOT / "src" / "utils"
INPUT_DIR = SRC_DIR / "input"
VALIDATORS_DIR = (
    SRC_DIR / "plugins" / "module_utils" / "input_validation" / "validators"
)
SCHEMA_DIR = SRC_DIR / "plugins" / "module_utils" / "input_validation" / "schema"
PIPELINE_DIR = REPO_ROOT / "test" / "pipeline"


@pytest.fixture
def repo_root():
    """Return the repository root path."""
    return REPO_ROOT


@pytest.fixture
def src_dir():
    """Return the src/utils directory path."""
    return SRC_DIR


@pytest.fixture
def input_dir():
    """Return the src/utils/input/ directory path."""
    return INPUT_DIR


@pytest.fixture
def validators_dir():
    """Return the collect_pxe validators directory path."""
    return VALIDATORS_DIR


@pytest.fixture
def schema_dir():
    """Return the collect_pxe schema directory path."""
    return SCHEMA_DIR


@pytest.fixture
def pipeline_dir():
    """Return the test/pipeline/ directory path."""
    return PIPELINE_DIR
