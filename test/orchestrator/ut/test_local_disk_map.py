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

"""Approved disk map and status-file contracts (ER-ORCH-011 TC-UT-003)."""

import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_PLUGIN_ROOT = REPO_ROOT / "src" / "orchestrator" / "plugins"
if str(SOURCE_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_PLUGIN_ROOT))

from module_utils.orchestrator_validation.validators import (  # noqa: E402
    local_disk_map,
)

KUBE_NODE_GROUP = "service_kube_node_x86_64"
CONTROL_PLANE_GROUP = "service_kube_control_plane_x86_64"
NODE_GROUPS = {
    "10.60.0.2": CONTROL_PLANE_GROUP,
    "10.60.0.11": KUBE_NODE_GROUP,
    "10.60.0.13": KUBE_NODE_GROUP,
}
KNOWN_GROUPS = {KUBE_NODE_GROUP, CONTROL_PLANE_GROUP}
LOCAL_STORAGE: list[dict[str, Any]] = [
    {
        "name": "etcd_disk",
        "purpose": "etcd",
        "disk_type": "boss",
        "disk_identity": "serial",
        "functional_group_prefix": ["service_kube_control_plane"],
    },
    {
        "name": "kafka_disk",
        "purpose": "kafka",
        "disk_type": "nvme",
        "disk_identity": "serial",
        "functional_group_prefix": ["service_kube_node"],
        "node_overrides": [{"node": "10.60.0.13", "disk_id": "S4EVNX0R901234"}],
    },
]


def _rows() -> list[dict[str, Any]]:
    return local_disk_map.build_map_rows(LOCAL_STORAGE, NODE_GROUPS, KNOWN_GROUPS)


def _by_node(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(row["node"], row["entry"]): row for row in rows}


def test_rows_are_built_from_the_declaration_without_row_state():
    """ORCH_UT_402: One row per node and entry, with the override disk_id and no status."""
    rows = _by_node(_rows())

    assert set(rows) == {
        ("10.60.0.2", "etcd_disk"),
        ("10.60.0.11", "kafka_disk"),
        ("10.60.0.13", "kafka_disk"),
    }
    assert rows[("10.60.0.13", "kafka_disk")]["disk_id"] == "S4EVNX0R901234"
    assert rows[("10.60.0.11", "kafka_disk")]["disk_id"] == ""
    assert rows[("10.60.0.2", "etcd_disk")]["disk_type"] == "boss"
    assert all("status" not in row for row in rows.values())


def test_written_map_returns_the_row_for_a_node(tmp_path):
    """ORCH_UT_403: A valid map returns the rows of the requested node."""
    path = local_disk_map.write_approved_map(
        str(tmp_path / "kafka_disk_mapping"), LOCAL_STORAGE, NODE_GROUPS, KNOWN_GROUPS
    )

    rows = local_disk_map.load_node_rows(path, "10.60.0.13")

    assert [row["entry"] for row in rows] == ["kafka_disk"]
    assert rows[0]["disk_id"] == "S4EVNX0R901234"
    assert json.loads(Path(path).read_text(encoding="utf-8"))["checksum"].startswith("sha256:")


def test_edited_rows_fail_the_checksum(tmp_path):
    """ORCH_UT_404: A map whose rows were changed after writing fails closed."""
    path = local_disk_map.write_approved_map(
        str(tmp_path), LOCAL_STORAGE, NODE_GROUPS, KNOWN_GROUPS
    )
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    document["rows"][0]["disk_id"] = "TAMPERED"
    Path(path).write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ValueError, match="checksum"):
        local_disk_map.load_node_rows(path, "10.60.0.13")


def test_node_missing_from_the_map_is_reported_by_name(tmp_path):
    """ORCH_UT_405: A node with no row fails and the message names the node."""
    path = local_disk_map.write_approved_map(
        str(tmp_path), LOCAL_STORAGE, NODE_GROUPS, KNOWN_GROUPS
    )

    with pytest.raises(ValueError, match="10.60.0.99"):
        local_disk_map.load_node_rows(path, "10.60.0.99")


def test_map_directory_follows_the_nfs_k8s_mount_point():
    """ORCH_UT_406: The map folder is kafka_disk_mapping under the nfs_k8s mount point."""
    storage = {"mounts": [{"name": "nfs_k8s", "mount_point": "/srv/k8s_share"}]}

    assert local_disk_map.resolve_map_dir(storage) == "/srv/k8s_share/kafka_disk_mapping"
    with pytest.raises(ValueError):
        local_disk_map.resolve_map_dir({"mounts": []})


def test_status_files_are_written_per_node_and_listed(tmp_path):
    """ORCH_UT_407: Each node owns one status file and the view lists every file."""
    local_disk_map.write_node_status(str(tmp_path), "10.60.0.11", "kafka_disk", "kafka", "ok", "", "")
    local_disk_map.write_node_status(
        str(tmp_path), "10.60.0.13", "kafka_disk", "kafka", "failed", "disk not found", "fix the disk"
    )

    view = {record["node"]: record for record in local_disk_map.read_status_view(str(tmp_path))}

    assert sorted(path.name for path in tmp_path.glob("status-*.json")) == [
        "status-10.60.0.11.json",
        "status-10.60.0.13.json",
    ]
    assert view["10.60.0.11"]["result"] == "ok"
    assert view["10.60.0.13"]["result"] == "failed"
    assert view["10.60.0.13"]["reason"] == "disk not found"
    assert view["10.60.0.13"]["action"] == "fix the disk"
