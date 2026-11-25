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


def _setup_task_text():
    return (SRC / "orchestrator/roles/orchestrator_setup/tasks/main.yml").read_text(
        encoding="utf-8"
    )


def test_effective_mapping_is_built_for_every_tag():
    text = _setup_task_text()
    start = text.index("- name: Build effective PXE mapping without comments")
    block = text[start:text.index("# Step 7:", start)]
    when = block.split("block:")[0]
    assert "omnia_run_tags" not in when and "tags" not in when
    assert 'mode: "0600"' in block


def test_effective_mapping_regex_removes_comments_and_blanks():
    from ansible.plugins.filter.core import regex_replace

    raw = "# top\r\nHDR,A\nx,1\n#c,2\n   # c3,3\n\ny,4\n  # last"
    out = regex_replace(raw, r"(?m)^[ \t]*(#[^\n]*)?\r?\n", "")
    out = regex_replace(out, r"(?m)^[ \t]*#[^\n]*$", "")
    assert out == "HDR,A\nx,1\ny,4\n"


def test_orchestrator_roles_prefer_effective_mapping_with_fallback():
    for rel in (
        "roles/passwordless_ssh/tasks/build_host_lists.yml",
        "roles/mount_config/tasks/build_host_mount_map.yml",
        "roles/k8s_config/tasks/create_k8s_config_nfs.yml",
        "roles/deploy_openchami/tasks/configs/ochami.yml",
        "roles/deploy_openchami/tasks/refresh_openchami_configs.yml",
        "roles/provision_common/tasks/register_nodes.yml",
        "roles/pxe_boot_inventory/tasks/main.yml",
        "roles/slurm_config/tasks/inject_ib_nodeaddr.yml",
        "roles/orchestrator_functional_groups/tasks/main.yml",
        "roles/ib_ipv6_config/defaults/main.yml",
    ):
        text = (SRC / "orchestrator" / rel).read_text(encoding="utf-8")
        assert "pxe_mapping_effective_path" in text, rel


def test_orphan_preview_precedes_deletion():
    text = (SRC / "orchestrator/playbooks/provision/provision_preamble.yml").read_text(
        encoding="utf-8"
    )
    preview = text.index("Preview SMD entries that are no longer in the PXE mapping")
    warn = text.index("Warn before removing nodes that were deleted or commented out")
    delete = text.index("Clean up orphaned SMD entries from previous deployments")
    assert preview < warn < delete
    assert "check_mode: true" in text[preview:warn]
