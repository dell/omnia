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

"""Local-storage declaration validation contracts (ER-ORCH-011 TC-UT-001, TC-UT-004)."""

import copy
import json
import logging
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
ORCHESTRATOR_ROOT = REPO_ROOT / "src" / "orchestrator"
SOURCE_PLUGIN_ROOT = ORCHESTRATOR_ROOT / "plugins"
if str(SOURCE_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_PLUGIN_ROOT))

from module_utils.orchestrator_validation.core import (  # noqa: E402
    validation_engine as engine,
)
from module_utils.orchestrator_validation.validators import (  # noqa: E402
    storage_config_validator,
)
from module_utils.orchestrator_validation.validators.pxe_mapping_validator import (  # noqa: E402
    CANONICAL_HEADERS,
)

SCHEMA_DIR = SOURCE_PLUGIN_ROOT / "module_utils" / "orchestrator_validation" / "schema"
STORAGE_SCHEMA = json.loads((SCHEMA_DIR / "storage_config.json").read_text(encoding="utf-8"))
OMNIA_SCHEMA = json.loads((SCHEMA_DIR / "omnia_config.json").read_text(encoding="utf-8"))
LOGGER = logging.getLogger("local-storage-validation-test")

MAPPING_ROWS = (
    ("service_kube_control_plane_x86_64", "10.60.0.2", "cp1"),
    ("service_kube_node_x86_64", "10.60.0.11", "w1"),
    ("fg_custom_x86_64", "10.60.0.21", "f1"),
)


def _etcd(**extra: Any) -> dict[str, Any]:
    """Return a valid etcd entry on the control-plane group, with overrides applied."""
    entry = {
        "name": "etcd_disk",
        "purpose": "etcd",
        "functional_group_prefix": ["service_kube_control_plane"],
        "disk_type": "boss",
        "fs_type": "ext4",
        "mount_options": "noatime",
    }
    entry.update(extra)
    return entry


def _kafka(**extra: Any) -> dict[str, Any]:
    """Return a valid Kafka entry on the worker group, with overrides applied."""
    entry = {
        "name": "kafka_disk",
        "purpose": "kafka",
        "functional_group_prefix": ["service_kube_node"],
        "disk_type": "nvme",
        "volume_group": "omnia-kafka-vg",
        "mount_options": "noatime,nodiratime",
    }
    entry.update(extra)
    return entry


def _schema_errors(entries: list[dict[str, Any]]) -> list[str]:
    return engine.schema(
        {"local_storage": entries}, STORAGE_SCHEMA, "storage_config.yml", LOGGER
    )


@pytest.fixture(name="project_dir")
def _project_dir(tmp_path: Path) -> Path:
    """Return a project input directory holding a PXE mapping with three groups."""
    lines = [",".join(CANONICAL_HEADERS)]
    for number, (group, admin_ip, host) in enumerate(MAPPING_ROWS, start=1):
        values = dict.fromkeys(CANONICAL_HEADERS, "")
        values.update(
            FUNCTIONAL_GROUP_NAME=group,
            GROUP_NAME=f"g{number}",
            SERVICE_TAG=f"T{number}",
            HOSTNAME=host,
            ADMIN_MAC=f"aa:bb:cc:dd:ee:{number:02d}",
            ADMIN_IP=admin_ip,
        )
        lines.append(",".join(values[header] for header in CANONICAL_HEADERS))
    (tmp_path / "pxe_mapping_file.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return tmp_path


def _semantic_errors(entries: list[dict[str, Any]], project_dir: Path) -> list[str]:
    return storage_config_validator.validate(
        {"mounts": [], "local_storage": entries}, {}, {}, str(project_dir)
    )


def test_valid_etcd_and_kafka_entries_pass(project_dir):
    """ORCH_UT_390: An etcd entry on control plane and a Kafka entry on workers pass."""
    entries = [_etcd(), _kafka()]

    assert _schema_errors(entries) == []
    assert _semantic_errors(entries, project_dir) == []


@pytest.mark.parametrize("extra", [{"fs_type": "ext4"}, {"mount_point": "/var/lib/etcd"}])
def test_kafka_entry_rejects_fs_type_and_mount_point(extra):
    """ORCH_UT_391: A Kafka entry carries no fs_type or mount_point; TopoLVM owns the filesystem."""
    assert _schema_errors([_kafka(**extra)])


def test_missing_volume_group_names_the_entry():
    """ORCH_UT_392: A Kafka entry without volume_group fails and the error names the entry."""
    entry = _kafka()
    del entry["volume_group"]

    errors = _schema_errors([entry])

    assert len(errors) == 1
    assert "'volume_group' is a required property" in errors[0]
    assert "local_storage entry 'kafka_disk'" in errors[0]


def test_disk_type_outside_enum_lists_allowed_values():
    """ORCH_UT_393: An unsupported disk_type fails and lists the allowed values."""
    errors = _schema_errors([_kafka(disk_type="sata")])

    assert len(errors) == 1
    assert "['boss', 'hdd', 'ssd', 'nvme']" in errors[0]


@pytest.mark.parametrize(("length", "valid"), [(1, True), (64, True), (65, False)])
def test_entry_name_length_boundary(length, valid):
    """ORCH_UT_394: Entry names of 1 and 64 characters pass; 65 characters fail."""
    errors = _schema_errors([_kafka(name="a" * length)])

    assert (errors == []) is valid
    if not valid:
        assert ".name:" in errors[0]


@pytest.mark.parametrize(
    ("mount_point", "valid"),
    [(None, True), ("/var/lib/etcd", True), ("/data/etcd", False)],
)
def test_etcd_mount_point_is_fixed(mount_point, valid):
    """ORCH_UT_395: The only allowed etcd mount_point is /var/lib/etcd."""
    extra = {} if mount_point is None else {"mount_point": mount_point}

    assert (_schema_errors([_etcd(**extra)]) == []) is valid


def test_removed_etcd_on_local_disk_key_points_to_local_storage():
    """ORCH_UT_396: etcd_on_local_disk is rejected and the error points to a purpose etcd entry."""
    document = yaml.safe_load((ORCHESTRATOR_ROOT / "input" / "omnia_config.yml").read_text(encoding="utf-8"))
    assert engine.schema(document, OMNIA_SCHEMA, "omnia_config.yml", LOGGER) == []
    rejected = copy.deepcopy(document)
    rejected["service_k8s_cluster"][0]["etcd_on_local_disk"] = True

    errors = engine.schema(rejected, OMNIA_SCHEMA, "omnia_config.yml", LOGGER)

    assert len(errors) == 1
    assert "'etcd_on_local_disk' was unexpected" in errors[0]
    assert "local_storage entry with purpose 'etcd'" in errors[0]


def test_other_unknown_cluster_key_gets_no_etcd_hint():
    """ORCH_UT_397: Only the removed key carries the etcd hint."""
    document = yaml.safe_load((ORCHESTRATOR_ROOT / "input" / "omnia_config.yml").read_text(encoding="utf-8"))
    document["service_k8s_cluster"][0]["bogus_key"] = True

    errors = engine.schema(document, OMNIA_SCHEMA, "omnia_config.yml", LOGGER)

    assert len(errors) == 1
    assert "etcd" not in errors[0]


@pytest.mark.parametrize(
    ("entries", "fragments"),
    [
        ([_kafka(functional_group_prefix=["service_kube_control_plane"])], ["kafka_disk", "service_kube_control_plane", "worker groups"]),
        ([_etcd(functional_group_prefix=["service_kube_node"])], ["etcd_disk", "control-plane groups"]),
        ([_kafka(functional_group_prefix=["slurm_node"])], ["kafka_disk", "slurm_node"]),
        ([_kafka(functional_group_prefix=["fg_custom"])], ["kafka_disk", "fg_custom"]),
        ([_etcd(mount_options="defaults,nofail")], ["etcd_disk", "nofail"]),
        ([_kafka(node_overrides=[{"node": "10.60.0.2", "disk_id": "S1"}])], ["10.60.0.2", "kafka_disk"]),
    ],
    ids=["kafka-on-control-plane", "etcd-on-worker", "slurm-prefix", "fg-group", "etcd-nofail", "override-outside-group"],
)
def test_semantic_rules_reject_invalid_combinations(entries, fragments, project_dir):
    """ORCH_UT_398: Each semantic rule rejects its violation and names the entry."""
    errors = _semantic_errors(entries, project_dir)

    assert errors
    joined = " ".join(errors)
    for fragment in fragments:
        assert fragment in joined


def test_override_for_a_node_in_the_group_is_accepted(project_dir):
    """ORCH_UT_399: A node_overrides entry for a node inside the group passes."""
    entries = [_kafka(node_overrides=[{"node": "10.60.0.11", "disk_id": "S1"}])]

    assert _semantic_errors(entries, project_dir) == []


def test_two_entries_of_one_purpose_on_one_group_are_rejected(project_dir):
    """ORCH_UT_400: Two Kafka entries that match one node fail and name both entries."""
    errors = _semantic_errors([_kafka(name="kafka_a"), _kafka(name="kafka_b")], project_dir)

    assert errors
    assert "kafka_a" in " ".join(errors) and "kafka_b" in " ".join(errors)


def test_every_declaration_error_is_listed_together(project_dir):
    """ORCH_UT_401: Several declaration errors are reported in one pass, not one at a time."""
    entries = [
        _kafka(name="kafka_cp", functional_group_prefix=["service_kube_control_plane"]),
        _etcd(mount_options="defaults,nofail"),
        _kafka(name="kafka_out", node_overrides=[{"node": "10.60.0.2", "disk_id": "S1"}]),
    ]

    joined = " ".join(_semantic_errors(entries, project_dir))

    assert "kafka_cp" in joined
    assert "nofail" in joined
    assert "kafka_out" in joined


@pytest.mark.parametrize(
    ("override", "valid"),
    [
        ({"node": "10.60.0.11", "enabled": False}, True),
        ({"node": "10.60.0.10-10.60.0.12", "enabled": False}, True),
        ({"node": "10.60.0.11", "disk_id": "S1", "enabled": True}, True),
        ({"node": "10.60.0.11", "enabled": False, "disk_id": "S1"}, False),
        ({"node": "10.60.0.11", "enabled": False, "disk_type": "ssd"}, False),
        ({"node": "10.60.0.11", "enabled": True}, False),
        ({"node": "10.60.0.11"}, False),
        ({"node": "10.60.0.11", "enabled": "no"}, False),
    ],
    ids=["disabled", "disabled-range", "enabled-true-with-disk", "disabled-with-disk-id",
         "disabled-with-disk-type", "enabled-true-without-disk", "no-disk-id", "enabled-not-bool"],
)
def test_node_override_schema_for_enabled(override, valid):
    """ORCH_UT_482: enabled false needs no disk fields and allows none; otherwise disk_id is required."""
    assert (_schema_errors([_kafka(node_overrides=[override])]) == []) is valid


def test_disabled_range_covering_a_group_node_passes(project_dir):
    """ORCH_UT_483: A disabled range that covers a worker passes semantic validation."""
    entries = [_etcd(), _kafka(node_overrides=[{"node": "10.60.0.10-10.60.0.12", "enabled": False}])]

    assert _schema_errors(entries) == []
    assert _semantic_errors(entries, project_dir) == []


@pytest.mark.parametrize(
    ("entries", "fragments"),
    [
        ([_etcd(node_overrides=[{"node": "10.60.0.2", "enabled": False}])],
         ["etcd_disk", "allowed only for purpose 'kafka'"]),
        ([_kafka(node_overrides=[{"node": "10.60.0.10-10.60.0.12", "disk_id": "S1"}])],
         ["10.60.0.10-10.60.0.12", "allowed only with enabled: false"]),
        ([_kafka(node_overrides=[{"node": "10.60.0.12-10.60.0.10", "enabled": False}])],
         ["not a valid IP range", "start is after end"]),
        ([_kafka(node_overrides=[{"node": "10.60.0.50-10.60.0.60", "enabled": False}])],
         ["matches no node", "10.60.0.50-10.60.0.60"]),
        ([_kafka(node_overrides=[{"node": "10.60.0.11", "disk_id": "S1"},
                                 {"node": "10.60.0.10-10.60.0.12", "enabled": False}])],
         ["10.60.0.11", "more than one node_overrides entry"]),
    ],
    ids=["etcd-disabled", "range-with-disk-id", "reversed-range", "range-no-match", "override-conflict"],
)
def test_disabled_and_range_rules_reject_invalid_overrides(entries, fragments, project_dir):
    """ORCH_UT_484: Each enabled/range rule rejects its violation with a message naming it."""
    joined = " ".join(_semantic_errors(entries, project_dir))

    for fragment in fragments:
        assert fragment in joined, joined
