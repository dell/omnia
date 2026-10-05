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

"""Contracts for functional-group configuration resolution and validation."""

import importlib.util
import json
import logging
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft7Validator


REPO_ROOT = Path(__file__).resolve().parents[3]
ORCHESTRATOR_ROOT = REPO_ROOT / "src" / "orchestrator"
SOURCE_PLUGIN_ROOT = ORCHESTRATOR_ROOT / "plugins"
if str(SOURCE_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_PLUGIN_ROOT))

from module_utils.orchestrator_validation.validators import (  # noqa: E402
    functional_group_config_validator as functional_validator,
)


def _load_source_module(name, relative_path):
    path = ORCHESTRATOR_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


resolver = _load_source_module(
    "functional_group_resolver",
    "plugins/module_utils/functional_group_resolver.py",
)


IMAGE = {
    "kernel": "boot-images/research/vmlinuz-x86_64",
    "initrd": "boot-images/research/initramfs-x86_64.img",
    "rootfs": "boot-images/research/rootfs-x86_64.squashfs",
}
DOMAIN_INIT = ORCHESTRATOR_ROOT / "domain-init.sh"


def _write_mapping(path, functional_group="research_rhel_10_0_x86_64"):
    path.write_text(
        "FUNCTIONAL_GROUP_NAME,GROUP_NAME,SERVICE_TAG,PARENT_SERVICE_TAG,"
        "HOSTNAME,ADMIN_MAC,ADMIN_IP,BMC_MAC,BMC_IP,IB_NIC_NAME,IB_IP\n"
        f"{functional_group},group-a,tag-1,,node-1,00:11:22:33:44:55,"
        "192.0.2.10,00:11:22:33:44:66,192.0.2.11,,\n",
        encoding="utf-8",
    )


def _validate(tmp_path, config, group="research_rhel_10_0_x86_64", **orchestrator):
    mapping = tmp_path / "pxe_mapping_file.csv"
    _write_mapping(mapping, group)
    return functional_validator.validate(
        config, {"pxe_mapping_file_path": str(mapping), **orchestrator}, str(tmp_path)
    )


def _run_domain_init(script, *args, domain_init=DOMAIN_INIT, stdin=subprocess.DEVNULL):
    return subprocess.run(
        ["bash", "-c", f'source "$1"; shift; {script}', "bash", str(domain_init), *args],
        check=False,
        capture_output=True,
        text=True,
        stdin=stdin,
    )


def test_group_resolution_preserves_precedence_empty_inheritance_and_provenance():
    """ORCH_UT_110: Group/common/legacy/default resolution is deterministic."""
    config = {
        "common": {
            "boot_kernel_params": "audit=1",
            "cloud_init": {"config_file": "/input/common-x86_64.yml"},
        },
        "groups": {
            "research_rhel_10_0_x86_64": {
                "boot_kernel_params": "",
                "post_config": [{"runcmd": ["echo ready"]}],
                "image_override": IMAGE,
            }
        },
    }

    resolved = resolver.resolve_group(config, "research_rhel_10_0_x86_64", "legacy=1")
    other = resolver.resolve_group(config, "other_rhel_10_0_x86_64")

    assert resolved.boot_kernel_params == ("audit=1", "common")
    assert resolved.cloud_init_config_file.source == "common"
    assert resolved.post_config.source == "group"
    assert resolved.image_override == (IMAGE, "group")
    assert other.image_override == ({}, "default")


def test_legacy_boot_parameters_are_only_a_fallback():
    """ORCH_UT_111: Deprecated boot parameters sit below new scopes."""
    legacy = resolver.resolve_group({}, "os_rhel_10_0_x86_64", "audit=1")
    common = resolver.resolve_group(
        {"common": {"boot_kernel_params": "numa=off"}}, "os_rhel_10_0_x86_64", "audit=1"
    )

    assert legacy.boot_kernel_params == ("audit=1", "legacy")
    assert common.boot_kernel_params == ("numa=off", "common")


def test_first_control_plane_runtime_name_uses_canonical_group():
    """ORCH_UT_112: The runtime _first control-plane group reads its mapping entry."""
    config = {"groups": {"service_kube_control_plane_x86_64": {"boot_kernel_params": "audit=1"}}}

    resolved = resolver.resolve_group(config, "service_kube_control_plane_first_x86_64")

    assert resolved.boot_kernel_params == ("audit=1", "group")
    assert (
        resolver.canonical_group_name("service_kube_control_plane_first_x86_64")
        == "service_kube_control_plane_x86_64"
    )
    assert resolver.canonical_group_name("slurm_node_x86_64") == "slurm_node_x86_64"


def test_cloud_init_sections_append_without_mutating_inputs():
    """ORCH_UT_113: Base cloud-init precedes ordered post-configuration."""
    base = {"runcmd": ["echo base"]}
    posts = [
        {"write_files": [{"path": "/etc/example", "content": "value"}]},
        {"runcmd": ["echo post"]},
    ]

    merged = resolver.merge_cloud_init_sections(base, posts)

    assert merged["runcmd"] == ["echo base", "echo post"]
    assert merged["write_files"][0]["path"] == "/etc/example"
    assert base == {"runcmd": ["echo base"]}


def test_domain_init_stages_only_missing_templates(tmp_path):
    """ORCH_UT_114: New templates reach old projects without overwrites."""
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.mkdir()
    destination.mkdir()
    (source / "existing.yml").write_text("new\n", encoding="utf-8")
    (source / "functional_group_config.yml").write_text(
        "common: {}\ngroups: {}\n", encoding="utf-8"
    )
    (source / "broken-link.yml").write_text("template\n", encoding="utf-8")
    (destination / "existing.yml").write_text("customer\n", encoding="utf-8")
    broken_link = destination / "broken-link.yml"
    broken_link.symlink_to(destination / "missing-customer-target.yml")

    result = _run_domain_init('_stage_new_files "$1" "$2"', str(source), str(destination))

    assert result.returncode == 0, result.stderr
    assert (destination / "existing.yml").read_text(encoding="utf-8") == "customer\n"
    assert (destination / "functional_group_config.yml").is_file()
    assert broken_link.is_symlink()
    assert not broken_link.exists()


@pytest.mark.parametrize("existing", [False, True])
def test_domain_init_copy_input_files_fresh_and_existing_projects(tmp_path, existing):
    """ORCH_UT_115: Staging completes under set -e for fresh and existing projects."""
    script_dir = tmp_path / "domain"
    (script_dir / "input").mkdir(parents=True)
    for name in ("a_config.yml", "functional_group_config.yml", "z_last.yml"):
        (script_dir / "input" / name).write_text(f"{name}: template\n", encoding="utf-8")
    project = tmp_path / "data" / "input" / "proj"
    if existing:
        project.mkdir(parents=True)
        (project / "a_config.yml").write_text("customer\n", encoding="utf-8")

    # SCRIPT_DIR is readonly and derived from the script location, so run a
    # copy placed beside the fake input templates.
    domain_init = script_dir / "domain-init.sh"
    domain_init.write_text(DOMAIN_INIT.read_text(encoding="utf-8"), encoding="utf-8")

    result = _run_domain_init(
        'set -euo pipefail; ORCHESTRATOR_DATA_PATH="$1"; '
        'OMNIA_PROJECT_NAME=proj; copy_input_files; echo DONE',
        str(tmp_path / "data"),
        domain_init=domain_init,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "DONE" in result.stdout
    assert (project / "functional_group_config.yml").is_file()
    assert (project / "z_last.yml").is_file()
    expected = "customer\n" if existing else "a_config.yml: template\n"
    assert (project / "a_config.yml").read_text(encoding="utf-8") == expected


def test_functional_group_validator_treats_empty_template_as_inactive(tmp_path):
    """ORCH_UT_116: Empty input is inactive; legacy conflicts are per field."""
    legacy_cloud_init = {"additional_cloud_init_config_file": "/legacy/cloud-init.yml"}

    assert not _validate(tmp_path, {"common": {}, "groups": {}}, **legacy_cloud_init)
    assert not _validate(tmp_path, {"common": None, "groups": None}, **legacy_cloud_init)
    assert not _validate(
        tmp_path, {"common": {"boot_kernel_params": "audit=1"}}, **legacy_cloud_init
    )
    errors = _validate(
        tmp_path, {"common": {"post_config": [{"runcmd": ["echo x"]}]}}, **legacy_cloud_init
    )
    assert any("additional_cloud_init_config_file" in error for error in errors)

    errors = _validate(
        tmp_path, {"common": {"boot_kernel_params": "audit=1"}}, boot_kernel_params="numa=off"
    )
    assert any("deprecated" in error for error in errors)
    assert not _validate(tmp_path, {"common": {}}, boot_kernel_params="numa=off")
    errors = _validate(tmp_path, {"common": {}}, boot_kernel_params="selinux=1")
    assert any("protected kernel parameter 'selinux'" in error for error in errors)


@pytest.mark.parametrize(
    "params, expected",
    [
        ("root=/dev/unsafe", "protected kernel parameter 'root'"),
        ("selinux=1 ip6=on ds=nocloud", "protected kernel parameter 'ds'"),
        ('x="\nfoo=bar', "is not a valid kernel parameter"),
        ("a=\x07b", "is not a valid kernel parameter"),
        ("a=b\\c", "is not a valid kernel parameter"),
    ],
)
def test_kernel_parameters_reject_protected_and_unsafe_values(tmp_path, params, expected):
    """ORCH_UT_117: Protected and quote/control-character parameters fail."""
    errors = _validate(
        tmp_path, {"groups": {"research_rhel_10_0_x86_64": {"boot_kernel_params": params}}}
    )

    assert any(expected in error for error in errors), errors


@pytest.mark.parametrize(
    "override, expected",
    [
        ({"rootfs": IMAGE["rootfs"]}, "missing kernel, initrd"),
        ({**IMAGE, "extra": "x"}, "unknown extra"),
        ({**IMAGE, "rootfs": "../../evil/rootfs rd.break"}, "must be an object key"),
        ({**IMAGE, "kernel": "http://attacker/vmlinuz"}, "must be an object key"),
        ({**IMAGE, "rootfs": "boot-images/rootfs-aarch64.squashfs"}, "image_override.rootfs names 'aarch64'"),
        ("boot-images/rootfs", "expected a mapping"),
    ],
)
def test_image_override_requires_complete_safe_tuple(tmp_path, override, expected):
    """ORCH_UT_118: image_override is an all-or-none safe artifact tuple."""
    errors = _validate(
        tmp_path, {"groups": {"research_rhel_10_0_x86_64": {"image_override": override}}}
    )

    assert any(expected in error for error in errors), errors


def test_valid_image_override_and_cloud_init_pass(tmp_path):
    """ORCH_UT_119: A complete tuple and project cloud-init file are accepted."""
    cloud_init = tmp_path / "research-x86_64.yml"
    cloud_init.write_text("runcmd:\n  - echo {{ v1.local_hostname }}\n", encoding="utf-8")

    assert not _validate(
        tmp_path,
        {
            "common": {},
            "groups": {
                "research_rhel_10_0_x86_64": {
                    "image_override": IMAGE,
                    "cloud_init": {"config_file": str(cloud_init)},
                }
            },
        },
    )
    assert not _validate(
        tmp_path, {"groups": {"research_rhel_10_0_x86_64": {"image_override": {}}}}
    )


def test_cloud_init_reference_rules(tmp_path):
    """ORCH_UT_120: Cloud-init files are project-local, non-empty, and plaintext."""
    outside = tmp_path.parent / f"{tmp_path.name}-outside-x86_64.yml"
    outside.write_text("runcmd:\n  - echo x\n", encoding="utf-8")
    empty = tmp_path / "empty-x86_64.yml"
    empty.write_text("# nothing\n", encoding="utf-8")
    vaulted = tmp_path / "vault-x86_64.yml"
    vaulted.write_text("$ANSIBLE_VAULT;1.1;AES256\n6162\n", encoding="utf-8")
    group = "research_rhel_10_0_x86_64"

    for path, expected in (
        (outside, "outside the allowed roots"),
        (empty, "is empty"),
        (vaulted, "vault-encrypted"),
    ):
        errors = _validate(
            tmp_path, {"groups": {group: {"cloud_init": {"config_file": str(path)}}}}
        )
        assert any(expected in error for error in errors), (path, errors)

    errors = _validate(
        tmp_path,
        {"common": {"post_config": [{"runcmd": ["echo 'password: hunter2 # $ANSIBLE_VAULT'"]}]}},
    )
    assert any("plaintext secret" in error for error in errors)


def test_functional_group_validator_checks_content_and_architecture(tmp_path):
    """ORCH_UT_121: Cloud-init content and architecture errors fail before mutation."""
    cloud_init = tmp_path / "cloud-init-aarch64.yml"
    cloud_init.write_text("packages:\n  - unsafe\n", encoding="utf-8")

    errors = _validate(
        tmp_path,
        {
            "groups": {
                "research_rhel_10_0_x86_64": {
                    "cloud_init": {"config_file": str(cloud_init)},
                    "image_override": {**IMAGE, "rootfs": "images/rootfs-aarch64"},
                }
            }
        },
    )

    assert any("platform-managed" in error and "packages" in error for error in errors)
    assert sum("targets architecture 'x86_64'" in error for error in errors) == 2


def test_unsupported_os_is_warning_not_failure(tmp_path, caplog):
    """ORCH_UT_122: Unsupported OS versions warn while valid input proceeds."""
    mapping = tmp_path / "pxe_mapping_file.csv"
    group = "research_rhel_11_0_x86_64"
    _write_mapping(mapping, group)

    warnings = []
    with caplog.at_level(logging.WARNING):
        errors = functional_validator.validate(
            {"groups": {group: {"boot_kernel_params": "audit=1"}}},
            {"pxe_mapping_file_path": str(mapping)},
            str(tmp_path),
            logging.getLogger("functional-group-test"),
            warnings,
        )

    assert not errors
    assert len(warnings) == 1
    assert "version '11.0'" in warnings[0]
    assert "outside the supported RHEL 10.0/10.2 set" in caplog.text


def test_common_cloud_init_architecture_is_checked_for_inheriting_groups(tmp_path):
    """ORCH_UT_123: Common paths cannot bypass per-group architecture checks."""
    cloud_init = tmp_path / "common-x86_64.yml"
    cloud_init.write_text("runcmd:\n  - echo ready\n", encoding="utf-8")

    errors = _validate(
        tmp_path,
        {"common": {"cloud_init": {"config_file": str(cloud_init)}}},
        group="research_rhel_10_0_aarch64",
    )

    assert any("targets architecture 'aarch64'" in error for error in errors)


def test_shipped_template_is_valid_and_inactive():
    """ORCH_UT_124: The staged template passes the schema and changes nothing."""
    schema = json.loads(
        (
            ORCHESTRATOR_ROOT
            / "plugins/module_utils/orchestrator_validation/schema/functional_group_config.json"
        ).read_text(encoding="utf-8")
    )
    template = yaml.safe_load(
        (ORCHESTRATOR_ROOT / "input/functional_group_config.yml").read_text(encoding="utf-8")
    )

    assert not list(Draft7Validator(schema).iter_errors(template))
    assert not resolver.has_effective_configuration(template)
