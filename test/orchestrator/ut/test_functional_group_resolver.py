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

"""Unit tests for functional-group configuration resolution and domain staging."""

import importlib.util
import json
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


def _load_source_module(name, relative_path):
    path = ORCHESTRATOR_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


resolver = _load_source_module(
    "functional_group_resolver",
    "plugins/module_utils/functional_group_resolver.py",
)
filter_plugin = _load_source_module(
    "filter_functional_group_config",
    "plugins/filter/functional_group_config.py",
)

IMAGE = {
    "kernel": "boot-images/research/vmlinuz-x86_64",
    "initrd": "boot-images/research/initramfs-x86_64.img",
    "rootfs": "boot-images/research/rootfs-x86_64.squashfs",
}
DOMAIN_INIT = ORCHESTRATOR_ROOT / "domain-init.sh"


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
            "fg_research_rhel_10_0_x86_64": {
                "boot_kernel_params": "",
                "image_override": IMAGE,
            }
        },
    }

    resolved = resolver.resolve_group(config, "fg_research_rhel_10_0_x86_64")
    other = resolver.resolve_group(config, "other_rhel_10_0_x86_64")

    assert resolved.boot_kernel_params == ("audit=1", "common")
    assert resolved.cloud_init_config_file.source == "common"
    assert resolved.image_override == (IMAGE, "group")
    assert other.image_override == ({}, "default")


def test_default_boot_parameters_fallback():
    """ORCH_UT_111: Default boot parameters apply when no scope overrides."""
    default = resolver.resolve_group({}, "os_rhel_10_0_x86_64")
    common = resolver.resolve_group(
        {"common": {"boot_kernel_params": "numa=off"}}, "os_rhel_10_0_x86_64"
    )

    assert default.boot_kernel_params == ("", "default")
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


def test_schema_validates_functional_group_config_template():
    """ORCH_UT_116: The shipped template satisfies the JSON schema."""
    schema = json.loads(
        (
            ORCHESTRATOR_ROOT
            / "plugins/module_utils/orchestrator_validation/schema/functional_group_config.json"
        ).read_text(encoding="utf-8")
    )
    template = yaml.safe_load(
        (ORCHESTRATOR_ROOT / "input/functional_group_config.yml").read_text(encoding="utf-8")
    )

    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(template))
    assert not errors, f"Schema errors: {errors}"
    assert not resolver.has_effective_configuration(template)


def test_filter_plugin_resolves_and_extracts_parameters():
    """ORCH_UT_117: Jinja filter plugin exposes resolve_functional_group_config."""
    filter_dict = filter_plugin.FilterModule().filters()
    assert "resolve_functional_group_config" in filter_dict

    config = {
        "groups": {
            "fg_compute_rhel_10_0_x86_64": {
                "boot_kernel_params": "quiet splash",
            }
        }
    }
    resolved = filter_dict["resolve_functional_group_config"](
        config, "fg_compute_rhel_10_0_x86_64"
    )
    assert resolved["boot_kernel_params"] == "quiet splash"
    assert "groups.fg_compute_rhel_10_0_x86_64" in resolved["boot_kernel_params_provenance"]
