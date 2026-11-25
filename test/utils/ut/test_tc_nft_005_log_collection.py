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
Unit tests for ER-ORCH-011 log collection extension (TC-NFT-005, NFR-4).

Validates:
- L1: Worker pod log directories (/var/log/pods, /var/log/containers) are configured
  in vars/main.yml and collected in k8s_logs.yml.
- L3: Per-node status files (status-<node>.json) from kafka_disk_mapping on the
  nfs_k8s share are collected during bundle.yml.
- Local disk prep log (/var/log/local-disk-prep.log) is configured for collection.
- Validation helper functions for TC-NFT-005 correctly verify bundle contents.
"""

# pylint: disable=missing-function-docstring,redefined-outer-name

from pathlib import Path
import tarfile
from unittest.mock import MagicMock
import yaml

import pytest

from library.functions.utils_func import (
    validate_bundle_worker_pod_logs,
    validate_bundle_local_storage_status_files,
)


@pytest.fixture
def role_dir():
    """Return path to log_collector role directory."""
    return Path(__file__).resolve().parents[3] / "src" / "utils" / "roles" / "log_collector"


@pytest.fixture
def vars_data(role_dir):
    """Load log_collector vars/main.yml."""
    vars_file = role_dir / "vars" / "main.yml"
    assert vars_file.exists(), f"vars/main.yml not found at {vars_file}"
    with open(vars_file, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_k8s_worker_log_dirs_configured(vars_data):
    """L1: k8s_worker_log_dirs must contain /var/log/pods/ and /var/log/containers/."""
    assert "k8s_worker_log_dirs" in vars_data
    worker_dirs = vars_data["k8s_worker_log_dirs"]
    assert "/var/log/pods/" in worker_dirs
    assert "/var/log/containers/" in worker_dirs


def test_local_disk_prep_log_files_configured(vars_data):
    """local-disk-prep.log must be collected from both masters and workers."""
    master_files = vars_data.get("k8s_master_log_files", [])
    worker_files = vars_data.get("k8s_worker_log_files", [])
    assert "/var/log/local-disk-prep.log" in master_files
    assert "/var/log/local-disk-prep.log" in worker_files


def test_storage_config_file_configured(vars_data):
    """storage_config_file must be configured in vars/main.yml."""
    assert "storage_config_file" in vars_data
    assert "storage_config.yml" in vars_data["storage_config_file"]


def test_k8s_logs_collects_worker_log_dirs(role_dir):
    """L1: k8s_logs.yml must contain tasks to stat, find, and fetch worker log directories."""
    tasks_file = role_dir / "tasks" / "k8s_logs.yml"
    assert tasks_file.exists()
    content = tasks_file.read_text(encoding="utf-8")

    assert "Stat k8s worker log directories" in content
    assert "k8s_worker_log_dirs" in content
    assert "Find files under existing k8s worker log directories" in content
    assert "Fetch files from k8s worker log directories" in content


def test_bundle_tasks_collect_nfs_status_files(role_dir):
    """L3: bundle.yml resolves nfs_k8s mount and collects status-*.json."""
    bundle_file = role_dir / "tasks" / "bundle.yml"
    assert bundle_file.exists()
    content = bundle_file.read_text(encoding="utf-8")

    assert "Check storage_config.yml exists on OIM" in content
    assert "Resolve kafka_disk_mapping directory from nfs_k8s mount" in content
    assert "kafka_disk_mapping" in content
    assert "status-*.json" in content
    assert "local_storage_status" in content


def test_validate_bundle_worker_pod_logs_detects_pod_logs(tmp_path):
    """TC-NFT-005 L1 validator finds pod and container log paths in tarball."""
    bundle_tar = tmp_path / "test_bundle.tar.gz"
    k8s_dir = tmp_path / "k8s" / "worker_node"
    pod_log_dir = k8s_dir / "var" / "log" / "pods" / "kafka_pod"
    pod_log_dir.mkdir(parents=True)
    (pod_log_dir / "0.log").write_text("kafka log output", encoding="utf-8")

    container_log_dir = k8s_dir / "var" / "log" / "containers"
    container_log_dir.mkdir(parents=True)
    (container_log_dir / "kafka.log").write_text("container log", encoding="utf-8")

    with tarfile.open(bundle_tar, "w:gz") as tar:
        tar.add(tmp_path / "k8s", arcname="k8s")

    mock_host = MagicMock()
    mock_host.run.return_value = MagicMock(
        rc=0,
        stdout=(
            "k8s/worker_node/var/log/pods/kafka_pod/0.log\n"
            "k8s/worker_node/var/log/containers/kafka.log\n"
        ),
        stderr="",
    )

    result = validate_bundle_worker_pod_logs(mock_host, str(bundle_tar))
    assert result["success"]
    assert len(result["found_pod_logs"]) > 0
    assert len(result["found_container_logs"]) > 0


def test_validate_bundle_local_storage_status_files_detects_status(tmp_path):
    """TC-NFT-005 L3 validator finds status-*.json files in tarball."""
    bundle_tar = tmp_path / "test_bundle.tar.gz"
    status_dir = tmp_path / "k8s" / "local_storage_status"
    status_dir.mkdir(parents=True)
    (status_dir / "status-10.60.0.11.json").write_text('{"result":"ok"}', encoding="utf-8")

    with tarfile.open(bundle_tar, "w:gz") as tar:
        tar.add(tmp_path / "k8s", arcname="k8s")

    mock_host = MagicMock()
    mock_host.run.return_value = MagicMock(
        rc=0,
        stdout="k8s/local_storage_status/status-10.60.0.11.json\n",
        stderr="",
    )

    result = validate_bundle_local_storage_status_files(mock_host, str(bundle_tar))
    assert result["success"]
    assert len(result["status_files"]) == 1
    assert "status-10.60.0.11.json" in result["status_files"][0]
