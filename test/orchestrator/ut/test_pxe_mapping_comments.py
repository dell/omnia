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

"""A commented-out PXE mapping row is treated as absent by every reader."""

# pylint: disable=wrong-import-position

import importlib.util
import re
from pathlib import Path

import pytest

from ut import source_loader  # noqa: F401  # initializes module_utils path

SRC = Path(__file__).resolve().parents[3] / "src"
HEADER = "FUNCTIONAL_GROUP_NAME,GROUP_NAME,SERVICE_TAG,HOSTNAME,ADMIN_MAC"
CSV = "\n".join(
    [
        "# leading comment",
        HEADER,
        "slurm_node_rhel_10_2_x86_64,grp1,TAG1,node1,aa:bb:cc:dd:ee:01",
        "#slurm_node_rhel_10_2_x86_64,grpC,TAG2,node2,aa:bb:cc:dd:ee:02",
        "   # indented,grpD,TAG3,node3,aa:bb:cc:dd:ee:03",
        "",
        "slurm_node_rhel_10_2_x86_64,grp4,TAG4,node4,aa:bb:cc:dd:ee:04",
    ]
)


def _load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(name="mapping")
def mapping_fixture(tmp_path):
    path = tmp_path / "pxe_mapping_file.csv"
    path.write_text(CSV, encoding="utf-8")
    return path


@pytest.mark.parametrize("domain", ["orchestrator", "utils"])
def test_pxe_mapping_read_skips_comments(domain, mapping):
    module = _load(SRC / domain / "plugins" / "modules" / "pxe_mapping_read.py")
    _, rows = module.read_mapping_rows(str(mapping))
    assert [row["SERVICE_TAG"] for row in rows] == ["TAG1", "TAG4"]


def test_pxe_mapping_read_all_commented(tmp_path):
    module = _load(SRC / "orchestrator" / "plugins" / "modules" / "pxe_mapping_read.py")
    path = tmp_path / "m.csv"
    path.write_text(f"{HEADER}\n#row1\n#row2\n", encoding="utf-8")
    _, rows = module.read_mapping_rows(str(path))
    assert rows == []


def test_generate_functional_groups_skips_comments(mapping):
    pytest.importorskip("yaml")
    module = _load(SRC / "orchestrator" / "plugins" / "modules" / "generate_functional_groups.py")
    groups, _ = module.parse_csv(str(mapping), None, categories={})
    assert sorted(groups) == ["grp1", "grp4"]


def test_ansible_readers_use_comment_aware_module():
    raw = re.compile(r"(community\.general|ansible\.builtin)\.read_csv:")
    for rel in (
        "roles/passwordless_ssh/tasks/build_host_lists.yml",
        "roles/pxe_boot_inventory/tasks/main.yml",
        "roles/mount_config/tasks/build_host_mount_map.yml",
        "roles/k8s_config/tasks/create_k8s_config_nfs.yml",
        "roles/deploy_openchami/tasks/configs/ochami.yml",
        "roles/deploy_openchami/tasks/refresh_openchami_configs.yml",
        "roles/provision_common/tasks/register_nodes.yml",
    ):
        text = (SRC / "orchestrator" / rel).read_text(encoding="utf-8")
        assert not raw.search(text), rel
        assert "pxe_mapping_read:" in text, rel
