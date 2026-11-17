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
"""Second-order Jinja protection for package_groups.yml loading."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = REPO_ROOT / "src/image_build_manager"
sys.path.insert(0, str(SRC_DIR / "plugins/module_utils/build_image"))

from yaml_safety import YamlSafetyError, load_runtime_yaml  # noqa: E402


def _write_package_groups(tmp_path, base_package):
    path = tmp_path / "package_groups.yml"
    path.write_text(
        "os: rhel\n"
        'os_version: "10.0"\n'
        f"base_packages: [{base_package!r}]\n"
        "functional_groups:\n"
        "  slurm_node_x86_64:\n"
        "    packages: [munge]\n",
        encoding="utf-8",
    )
    return path


def test_sample_package_groups_loads():
    data, exists = load_runtime_yaml(str(SRC_DIR / "input/package_groups.yml"))
    assert exists
    assert data["base_packages"]
    assert data["functional_groups"]


def test_literal_package_groups_returned_unchanged(tmp_path):
    data, _ = load_runtime_yaml(str(_write_package_groups(tmp_path, "bash")))
    assert data == {
        "os": "rhel",
        "os_version": "10.0",
        "base_packages": ["bash"],
        "functional_groups": {"slurm_node_x86_64": {"packages": ["munge"]}},
    }


@pytest.mark.parametrize(
    "payload",
    ["{{ lookup('pipe', 'id') }}", "{% if true %}x{% endif %}", "{# comment #}"],
)
def test_jinja_syntax_rejected(tmp_path, payload):
    with pytest.raises(YamlSafetyError) as err:
        load_runtime_yaml(str(_write_package_groups(tmp_path, payload)))
    assert err.value.code == "template_syntax_forbidden"


def test_jinja_in_functional_group_key_rejected(tmp_path):
    path = tmp_path / "package_groups.yml"
    path.write_text(
        'os: rhel\nos_version: "10.0"\nbase_packages: [bash]\n'
        "functional_groups:\n  \"{{ lookup('pipe', 'id') }}_x86_64\":\n"
        "    packages: [munge]\n",
        encoding="utf-8",
    )
    with pytest.raises(YamlSafetyError) as err:
        load_runtime_yaml(str(path))
    assert err.value.code == "template_syntax_forbidden"


def test_missing_package_groups_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_runtime_yaml(str(tmp_path / "package_groups.yml"))


def test_non_mapping_root_rejected(tmp_path):
    path = tmp_path / "package_groups.yml"
    path.write_text("- bash\n", encoding="utf-8")
    with pytest.raises(YamlSafetyError) as err:
        load_runtime_yaml(str(path))
    assert err.value.code == "mapping_required"


def test_sample_image_build_config_loads():
    data, exists = load_runtime_yaml(str(SRC_DIR / "input/image_build_config.yml"))
    assert exists
    assert "build_image" in data
    assert "s3_configurations" in data


def test_jinja_in_image_build_config_rejected(tmp_path):
    path = tmp_path / "image_build_config.yml"
    path.write_text(
        "s3_configurations: {provider: minio, endpoint_url: ''}\n"
        "aarch64_ssh_user: \"{{ lookup('pipe', 'id') }}\"\n",
        encoding="utf-8",
    )
    with pytest.raises(YamlSafetyError) as err:
        load_runtime_yaml(str(path))
    assert err.value.code == "template_syntax_forbidden"
