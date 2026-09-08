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
"""Unit tests for the version-aware repo_status.yml consumer."""

import importlib.util
from pathlib import Path
import sys
import types


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = (
    REPO_ROOT
    / "src/image_build_manager/plugins/modules/parse_repo_status.py"
)
SAMPLE_DIR = (
    REPO_ROOT / "src/image_build_manager/samples/repo_manager_output"
)


if "ansible" not in sys.modules:
    ansible = types.ModuleType("ansible")
    module_utils = types.ModuleType("ansible.module_utils")
    basic = types.ModuleType("ansible.module_utils.basic")

    class FakeAnsibleModule:  # pylint: disable=too-few-public-methods
        """Minimal import stub; module entry points are not exercised here."""

    basic.AnsibleModule = FakeAnsibleModule
    ansible.module_utils = module_utils
    sys.modules["ansible"] = ansible
    sys.modules["ansible.module_utils"] = module_utils
    sys.modules["ansible.module_utils.basic"] = basic


SPEC = importlib.util.spec_from_file_location("parse_repo_status", MODULE_PATH)
PARSE_REPO_STATUS = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(PARSE_REPO_STATUS)


def test_parse_multi_version_repo_manager_sample(tmp_path):
    """Both RHEL versions remain identifiable for later catalog filtering."""
    sample = (SAMPLE_DIR / "repo_status.yml").read_text(encoding="utf-8")
    rendered = tmp_path / "repo_status.yml"
    rendered.write_text(
        sample.replace("{{ admin_nic_ip }}", "192.0.2.10"),
        encoding="utf-8",
    )

    result = PARSE_REPO_STATUS.parse_repo_status(str(rendered))

    assert result["cluster_os_version"] == "10.0"
    assert result["cluster_os_versions"] == ["10.0", "10.2"]
    assert result["repo_port"] == 2225
    assert {repo["os_version"] for repo in result["repo_manager_repos_x86_64"]} == {
        "10.0",
        "10.2",
    }
    assert any(
        repo["name"] == "10_2_baseos"
        for repo in result["repo_manager_repos_x86_64"]
    )


def test_parse_internet_sample_uses_https_default_port():
    """The internet-only fixture derives port 443 from its first HTTPS URL."""
    result = PARSE_REPO_STATUS.parse_repo_status(
        str(SAMPLE_DIR / "repo_status_internet.yml")
    )

    assert result["repo_port"] == 443
    assert result["repo_cert_path"] == ""
    assert result["cluster_os_versions"] == ["10.0", "10.2"]
