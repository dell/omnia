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
Pytest configuration and fixtures for cadence unit tests.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

import pytest

# Add source directory to path
SRC_DIR = Path(__file__).parent.parent.parent.parent.parent.parent / "src" / "build_stream"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Import cadence_manager module directly since playbook-watcher is not a package
import importlib.util
spec = importlib.util.spec_from_file_location(
    "cadence_manager",
    SRC_DIR / "app" / "playbook-watcher" / "cadence_manager.py"
)
cadence_manager_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cadence_manager_module)
sys.modules["cadence_manager"] = cadence_manager_module


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_catalog_json():
    """Sample cadence catalog JSON content."""
    return {
        "catalog": {
            "schema_version": 2,
            "version": "1.0",
            "functional_layers": [],
            "groups": [],
            "packages": []
        }
    }


@pytest.fixture
def sample_cadence_config():
    """Sample cadence configuration."""
    return {
        "enabled": True,
        "interval_seconds": 3600,
        "catalog_filename": "cadence_catalog_rhel.json",
        "gitlab_repo_path": "/tmp/test_repo",
        "playbook_name": "repo_sync.yml",
        "sync_timeout_seconds": 1800,
        "sync_poll_interval_seconds": 5,
        "auto_bump_version": True,
        "version_bump_strategy": "patch",
        "git_author_name": "BuildStream Cadence",
        "git_author_email": "buildstream@omnia.local",
        "emit_audit_events": True,
        "log_level": "info"
    }


@pytest.fixture
def mock_omnia_data_path(temp_dir):
    """Mock OMNIA_DATA_PATH environment variable."""
    original = os.environ.get("OMNIA_DATA_PATH")
    os.environ["OMNIA_DATA_PATH"] = str(temp_dir)
    yield temp_dir
    if original:
        os.environ["OMNIA_DATA_PATH"] = original
    else:
        os.environ.pop("OMNIA_DATA_PATH", None)


@pytest.fixture
def mock_queue_dirs(temp_dir):
    """Create mock queue directory structure."""
    queue_dir = temp_dir / "build_stream" / "cadence_queue"
    for subdir in ["pending", "processing", "completed", "failed"]:
        (queue_dir / subdir).mkdir(parents=True, exist_ok=True)
    return queue_dir


@pytest.fixture
def mock_git_repo(temp_dir):
    """Create a mock Git repository."""
    import subprocess
    repo_dir = temp_dir / "test_repo"
    repo_dir.mkdir()
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True, capture_output=True)
    return repo_dir


@pytest.fixture
def mock_log_secure_info():
    """Mock log_secure_info function."""
    with patch("cadence_manager.log_secure_info") as mock:
        yield mock
