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

"""Unit contracts for the additional cloud-init configuration validator."""

import sys
from pathlib import Path

import pytest

# The validator lives in the src orchestrator plugins tree.  The UT conftest
# already adds the test plugin root; we also need the *src* plugin root so
# that ``module_utils.orchestrator_validation`` resolves.
_SRC_PLUGIN_ROOT = str(
    Path(__file__).resolve().parents[3] / "src" / "orchestrator" / "plugins"
)
if _SRC_PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, _SRC_PLUGIN_ROOT)

from module_utils.orchestrator_validation.validators import (
    additional_cloud_init_validator as validator,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _config(path: str) -> dict:
    """Return minimal orchestrator_config data pointing at *path*."""
    return {"additional_cloud_init_config_file": path}


def _write_yaml(tmp_path: Path, content: str, name: str = "aci.yml") -> str:
    """Write *content* to a temp file and return its absolute path."""
    target = tmp_path / name
    target.write_text(content, encoding="utf-8")
    return str(target)


def _write_mapping(tmp_path: Path, groups: list[str]) -> str:
    """Write a minimal PXE mapping CSV and return its absolute path."""
    lines = [
        "FUNCTIONAL_GROUP_NAME,GROUP_NAME,SERVICE_TAG,PARENT_SERVICE_TAG,"
        "HOSTNAME,ADMIN_MAC,ADMIN_IP,BMC_MAC,BMC_IP,IB_NIC_NAME,IB_IP"
    ]
    for idx, group in enumerate(groups, start=1):
        lines.append(
            f"{group},grp{idx},TAG{idx:04d},,node{idx},"
            f"aa:bb:cc:dd:ee:{idx:02x},10.0.0.{idx},"
            f"ff:ee:dd:cc:bb:{idx:02x},10.1.0.{idx},,"
        )
    mapping = tmp_path / "pxe_mapping_file.csv"
    mapping.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(mapping)


# ---------------------------------------------------------------------------
# Positive: feature disabled / valid configuration
# ---------------------------------------------------------------------------

def test_empty_path_disables_validation(tmp_path):
    """ORCH_UT_040: Empty config path disables validation with no errors."""
    errors = validator.validate(
        {"additional_cloud_init_config_file": ""}, str(tmp_path)
    )
    assert errors == []


def test_missing_key_disables_validation(tmp_path):
    """ORCH_UT_041: Absent config key disables validation with no errors."""
    errors = validator.validate({}, str(tmp_path))
    assert errors == []


def test_null_yaml_file_passes(tmp_path):
    """ORCH_UT_042: An empty/null YAML file passes (feature disabled)."""
    path = _write_yaml(tmp_path, "---\n")
    errors = validator.validate(_config(path), str(tmp_path))
    assert errors == []


def test_valid_common_section(tmp_path):
    """ORCH_UT_043: Valid common section with write_files and runcmd passes."""
    content = (
        "common:\n"
        "  write_files:\n"
        "    - path: /etc/motd\n"
        "      content: hello\n"
        "      permissions: '0644'\n"
        "  runcmd:\n"
        "    - echo done\n"
    )
    path = _write_yaml(tmp_path, content)
    errors = validator.validate(_config(path), str(tmp_path))
    assert errors == []


def test_valid_groups_section(tmp_path):
    """ORCH_UT_044: Valid per-FG groups section passes when FG exists."""
    _write_mapping(tmp_path, ["slurm_node_rhel_10_0_x86_64"])
    content = (
        "groups:\n"
        "  slurm_node_rhel_10_0_x86_64:\n"
        "    runcmd:\n"
        "      - echo setup\n"
    )
    path = _write_yaml(tmp_path, content)
    config = _config(path)
    config["pxe_mapping_file_path"] = str(tmp_path / "pxe_mapping_file.csv")
    errors = validator.validate(config, str(tmp_path))
    assert errors == []


def test_valid_common_and_groups_combined(tmp_path):
    """ORCH_UT_045: Combined common + groups configuration passes."""
    _write_mapping(tmp_path, ["slurm_node_rhel_10_0_x86_64"])
    content = (
        "common:\n"
        "  runcmd:\n"
        "    - echo common\n"
        "groups:\n"
        "  slurm_node_rhel_10_0_x86_64:\n"
        "    write_files:\n"
        "      - path: /tmp/test\n"
        "        content: data\n"
    )
    path = _write_yaml(tmp_path, content)
    config = _config(path)
    config["pxe_mapping_file_path"] = str(tmp_path / "pxe_mapping_file.csv")
    errors = validator.validate(config, str(tmp_path))
    assert errors == []


def test_empty_common_and_groups_passes(tmp_path):
    """ORCH_UT_046: Empty common/groups sections create no errors."""
    content = "common: {}\ngroups: {}\n"
    path = _write_yaml(tmp_path, content)
    errors = validator.validate(_config(path), str(tmp_path))
    assert errors == []


# ---------------------------------------------------------------------------
# Negative: file-level errors
# ---------------------------------------------------------------------------

def test_missing_config_file(tmp_path):
    """ORCH_UT_047: Missing config file produces an error."""
    errors = validator.validate(
        _config(str(tmp_path / "nonexistent.yml")), str(tmp_path)
    )
    assert len(errors) == 1
    assert "does not exist" in errors[0]


def test_invalid_yaml_syntax(tmp_path):
    """ORCH_UT_048: Malformed YAML produces a parse error."""
    path = _write_yaml(tmp_path, "common:\n  - bad: [unterminated\n")
    errors = validator.validate(_config(path), str(tmp_path))
    assert len(errors) == 1
    assert "Failed to parse YAML" in errors[0]


# ---------------------------------------------------------------------------
# Negative: document-level structure errors
# ---------------------------------------------------------------------------

def test_non_dict_root(tmp_path):
    """ORCH_UT_049: Non-dict YAML root is rejected."""
    path = _write_yaml(tmp_path, "- list_item\n")
    errors = validator.validate(_config(path), str(tmp_path))
    assert len(errors) == 1
    assert "must be a mapping" in errors[0]


def test_invalid_top_level_key(tmp_path):
    """ORCH_UT_050: Unknown top-level keys are rejected."""
    path = _write_yaml(tmp_path, "common: {}\nunknown_key: value\n")
    errors = validator.validate(_config(path), str(tmp_path))
    assert len(errors) == 1
    assert "unsupported" in errors[0]
    assert "unknown_key" in errors[0]


# ---------------------------------------------------------------------------
# Negative: prohibited and invalid section keys
# ---------------------------------------------------------------------------

def test_prohibited_key_in_common(tmp_path):
    """ORCH_UT_051: Prohibited key under common is rejected."""
    path = _write_yaml(tmp_path, "common:\n  bootcmd:\n    - reboot\n")
    errors = validator.validate(_config(path), str(tmp_path))
    assert len(errors) == 1
    assert "platform-managed" in errors[0]
    assert "bootcmd" in errors[0]


def test_prohibited_key_in_groups(tmp_path):
    """ORCH_UT_052: Prohibited key under a group section is rejected."""
    content = (
        "groups:\n"
        "  some_group:\n"
        "    network:\n"
        "      version: 2\n"
    )
    path = _write_yaml(tmp_path, content)
    errors = validator.validate(_config(path), str(tmp_path))
    assert any("platform-managed" in e and "network" in e for e in errors)


def test_prohibited_packages_key(tmp_path):
    """ORCH_UT_053: Packages key is specifically prohibited."""
    path = _write_yaml(tmp_path, "common:\n  packages:\n    - vim\n")
    errors = validator.validate(_config(path), str(tmp_path))
    assert len(errors) == 1
    assert "platform-managed" in errors[0]
    assert "packages" in errors[0]


def test_unknown_section_key(tmp_path):
    """ORCH_UT_054: Unknown key within a section is rejected."""
    path = _write_yaml(tmp_path, "common:\n  custom_directive: true\n")
    errors = validator.validate(_config(path), str(tmp_path))
    assert len(errors) == 1
    assert "unsupported" in errors[0]
    assert "custom_directive" in errors[0]


# ---------------------------------------------------------------------------
# Negative: runcmd validation
# ---------------------------------------------------------------------------

def test_runcmd_not_list(tmp_path):
    """ORCH_UT_055: runcmd as a non-list value is rejected."""
    path = _write_yaml(tmp_path, "common:\n  runcmd: echo hello\n")
    errors = validator.validate(_config(path), str(tmp_path))
    assert len(errors) == 1
    assert "must be a list" in errors[0]


def test_runcmd_non_string_entries(tmp_path):
    """ORCH_UT_056: Non-string entries in runcmd are rejected."""
    content = "common:\n  runcmd:\n    - 42\n    - true\n"
    path = _write_yaml(tmp_path, content)
    errors = validator.validate(_config(path), str(tmp_path))
    assert len(errors) == 2
    assert all("must be a string" in e for e in errors)


# ---------------------------------------------------------------------------
# Negative: write_files validation
# ---------------------------------------------------------------------------

def test_write_files_not_list(tmp_path):
    """ORCH_UT_057: write_files as a non-list value is rejected."""
    path = _write_yaml(tmp_path, "common:\n  write_files: not_a_list\n")
    errors = validator.validate(_config(path), str(tmp_path))
    assert len(errors) == 1
    assert "must be a list" in errors[0]


def test_write_files_missing_path(tmp_path):
    """ORCH_UT_058: write_files entry without path is rejected."""
    content = "common:\n  write_files:\n    - content: hello\n"
    path = _write_yaml(tmp_path, content)
    errors = validator.validate(_config(path), str(tmp_path))
    assert len(errors) == 1
    assert "path" in errors[0]
    assert "non-empty string" in errors[0]


# ---------------------------------------------------------------------------
# Negative: functional-group name validation
# ---------------------------------------------------------------------------

def test_invalid_fg_name(tmp_path):
    """ORCH_UT_059: Group name not in PXE mapping is rejected."""
    _write_mapping(tmp_path, ["slurm_node_rhel_10_0_x86_64"])
    content = (
        "groups:\n"
        "  nonexistent_group:\n"
        "    runcmd:\n"
        "      - echo test\n"
    )
    path = _write_yaml(tmp_path, content)
    config = _config(path)
    config["pxe_mapping_file_path"] = str(tmp_path / "pxe_mapping_file.csv")
    errors = validator.validate(config, str(tmp_path))
    assert len(errors) == 1
    assert "nonexistent_group" in errors[0]
    assert "not selected" in errors[0]


# ---------------------------------------------------------------------------
# Negative: multi-error reporting
# ---------------------------------------------------------------------------

def test_multi_error_reporting(tmp_path):
    """ORCH_UT_060: Multiple errors are collected in a single pass."""
    _write_mapping(tmp_path, ["slurm_node_rhel_10_0_x86_64"])
    content = (
        "bad_top_key: 1\n"
        "common:\n"
        "  packages:\n"
        "    - vim\n"
        "  runcmd: not_a_list\n"
        "groups:\n"
        "  missing_fg:\n"
        "    write_files:\n"
        "      - content: no_path\n"
    )
    path = _write_yaml(tmp_path, content)
    config = _config(path)
    config["pxe_mapping_file_path"] = str(tmp_path / "pxe_mapping_file.csv")
    errors = validator.validate(config, str(tmp_path))
    # Expect at least: bad_top_key, packages prohibited, runcmd not list,
    # missing_fg invalid, write_files[0] missing path
    assert len(errors) >= 5
