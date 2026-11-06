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

"""
Repo Manager System Test (ST) — Suite-Local Configuration.

Test Plan: BR-55868 — RHEL 10.2 Support for x86_64 Functional Groups
ER: ER-ORCH-010-rhel-10-2-x86-64-support

Reporting: Inherits from domain-level conftest.py (repo_manager/conftest.py)
"""

import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml

# ============================================================================
# Fixtures: Environment and Configuration
# ============================================================================

@pytest.fixture(scope="session")
def omnia_data_path():
    """Return OMNIA_DATA_PATH from environment or default."""
    return os.getenv("OMNIA_DATA_PATH", "/opt/omnia")


@pytest.fixture(scope="session")
def omnia_project_name():
    """Return OMNIA_PROJECT_NAME from environment or default."""
    return os.getenv("OMNIA_PROJECT_NAME", "project_default")


@pytest.fixture(scope="session")
def repo_status_path(omnia_data_path, omnia_project_name):
    """Return path to repo_status.yml."""
    return Path(omnia_data_path) / "repo_manager" / "output" / omnia_project_name / "repo_status.yml"


@pytest.fixture(scope="session")
def repo_status(repo_status_path):
    """Load repo_status.yml contract."""
    if not repo_status_path.exists():
        pytest.skip(f"repo_status.yml not found: {repo_status_path}")

    try:
        with open(repo_status_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        pytest.skip(f"Failed to load repo_status.yml: {str(e)}")


@pytest.fixture(scope="session")
def build_status_path(omnia_data_path, omnia_project_name):
    """Return path to build_status.yml."""
    return (
        Path(omnia_data_path) / "image_build_manager" / "output"
        / omnia_project_name / "build_status.yml"
    )


@pytest.fixture(scope="session")
def build_status(build_status_path):
    """Load build_status.yml contract."""
    if not build_status_path.exists():
        pytest.skip(f"build_status.yml not found: {build_status_path}")

    try:
        with open(build_status_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        pytest.skip(f"Failed to load build_status.yml: {str(e)}")


@pytest.fixture(scope="session")
def catalog_path(omnia_data_path):
    """Return path to catalog_rhel.json."""
    return Path(omnia_data_path) / "catalog" / "catalog_rhel.json"


@pytest.fixture(scope="session")
def catalog(catalog_path):
    """Load the RHEL catalog."""
    if not catalog_path.exists():
        pytest.skip(f"catalog_rhel.json not found: {catalog_path}")

    try:
        with open(catalog_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        pytest.skip(f"Failed to load catalog: {str(e)}")


# ============================================================================
# Fixtures: Test Logging and Reporting
# ============================================================================

@pytest.fixture
def test_logger():
    """Provide the TestLogger class from omnia_auto."""
    from omnia_auto import TestLogger as OmniaTestLogger
    return OmniaTestLogger


# ============================================================================
# Hooks: Test Collection
# ============================================================================

def pytest_collection_modifyitems(config, items):
    """Add ST-specific markers to all tests in this directory."""
    for item in items:
        # Add 'st' marker to all tests in this directory
        if "st" not in [marker.name for marker in item.iter_markers()]:
            item.add_marker(pytest.mark.st)
        # Add 'repo_manager' marker
        if "repo_manager" not in [marker.name for marker in item.iter_markers()]:
            item.add_marker(pytest.mark.repo_manager)


def pytest_configure(config):
    """Register ST-specific markers."""
    config.addinivalue_line("markers", "st: system test (spans multiple domains)")
    config.addinivalue_line("markers", "tier1: Tier 1 - Image Pipeline tests")
    config.addinivalue_line("markers", "rhel102: RHEL 10.2 EUS support tests")
    config.addinivalue_line("markers", "rhel100: RHEL 10.0 EUS support tests")
    config.addinivalue_line("markers", "repo_manager: repo_manager domain tests")
