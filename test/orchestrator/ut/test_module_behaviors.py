# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Deterministic behavior tests for Orchestrator custom modules."""

import csv
from types import SimpleNamespace

import pytest
import yaml

from ut import source_loader  # noqa: F401  pylint: disable=unused-import
from plugins.modules import (  # pylint: disable=wrong-import-order,import-error
    additional_images_collector,
    bulk_update_hosts,
    fetch_credential_rule,
    generate_functional_groups,
    generate_xname_in_mapping_file,
    slurm_conf,
    validate_credentials,
    validate_system_environment,
)
import library.functions as orchestrator_functions
from library.functions import host_func, slurm_func


pytestmark = pytest.mark.unit


def test_automated_pxe_paths_disable_the_tty_only_initial_pause(monkeypatch):
    """ORCH_UT_063: Automated PXE flows start bounded polling immediately."""
    captured = []

    def fake_run_playbook(**kwargs):
        captured.append(kwargs)
        return kwargs

    monkeypatch.setattr(
        orchestrator_functions, "_run_playbook", fake_run_playbook
    )
    caller_vars = {
        "preserved": "value",
        "node_registration_pause_minutes": 3,
    }

    orchestrator_functions.run_playbook(
        tag="execute", extra_vars=caller_vars
    )
    orchestrator_functions.run_playbook(tag="pxeboot")
    orchestrator_functions.run_playbook(tag="prepare")

    assert caller_vars["node_registration_pause_minutes"] == 3
    assert captured[0]["extra_vars"] == {
        "preserved": "value",
        "node_registration_pause_minutes": 0,
    }
    assert captured[1]["extra_vars"] == {
        "node_registration_pause_minutes": 0
    }
    assert "extra_vars" not in captured[2]


def test_catalog_image_collection_is_role_scoped_and_deduplicated():
    """ORCH_UT_052: Catalog images retain tags/digests without duplicates."""
    catalog = {
        "catalog": {
            "packages": {
                "tagged": {
                    "packagetype": "image",
                    "name": "registry.example/worker",
                    "tag": "1.2",
                },
                "pinned": {
                    "packagetype": "image",
                    "name": "registry.example/agent",
                    "digest": "sha256:abc",
                },
                "rpm": {"packagetype": "rpm", "name": "ignored"},
            },
            "groups": {
                "runtime": {
                    "components": ["tagged", "tagged", "pinned", "rpm"]
                }
            },
            "functionallayer": [{
                "name": "slurm_node_rhel_x86_64",
                "components": ["runtime"],
            }],
        }
    }
    result = additional_images_collector.collect_images_from_catalog(catalog)
    assert result == {
        "slurm_node": [
            {
                "package": "registry.example/worker",
                "tag": "1.2",
                "pull_ref": "registry.example/worker:1.2",
            },
            {
                "package": "registry.example/agent",
                "digest": "sha256:abc",
                "pull_ref": "registry.example/agent@sha256:abc",
            },
        ]
    }


def test_hosts_block_is_deterministic_and_cleanup_patterns_are_escaped():
    """ORCH_UT_053: Hosts updates are stable and regex-safe for FQDNs."""
    mapping = {"node.02": "192.0.2.12", "node.01": "192.0.2.11"}
    block = bulk_update_hosts._build_hosts_block(mapping)  # pylint: disable=protected-access
    assert block.splitlines()[1:3] == [
        "192.0.2.11 node.01",
        "192.0.2.12 node.02",
    ]
    cleanup = bulk_update_hosts._build_cleanup_sed(  # pylint: disable=protected-access
        mapping, ["retired+node"]
    )
    assert r"192\.0\.2\.11" in cleanup
    assert r"node\.01" in cleanup
    assert r"retired\+node" in cleanup


def test_credential_rule_lookup_and_boundary_validation():
    """ORCH_UT_054: Credential rules enforce names, bounds, and patterns."""
    rules = {
        "token": {
            "minLength": 3,
            "maxLength": 5,
            "pattern": r"^[A-Z]+$",
            "description": "uppercase token",
        }
    }
    assert fetch_credential_rule.fetch_rule("token", rules) == (
        True, "uppercase token"
    )
    assert not fetch_credential_rule.fetch_rule("missing", rules)[0]
    assert validate_credentials.validate_input("token", "ABC", rules)[0]
    assert not validate_credentials.validate_input("token", "AB", rules)[0]
    assert not validate_credentials.validate_input("token", "abc", rules)[0]


def test_functional_group_classification_prefers_specific_description():
    """ORCH_UT_055: Functional groups receive deterministic class metadata."""
    categories = {
        "slurm": {
            "patterns": [r"^slurm_"],
            "default_layer": "compute",
            "layer_rules": {"control": "management"},
            "default_description": "Slurm node",
            "description_map": {
                "slurm_": "generic",
                "slurm_control_": "controller",
            },
        }
    }
    assert generate_functional_groups.classify_functional_group(
        "slurm_control_node_x86_64", categories
    ) == ("slurm", "management", "controller")
    assert generate_functional_groups.classify_functional_group(
        "custom_accelerator", categories
    ) == ("custom", "compute", "User-Defined Functional Group")
    generated = generate_functional_groups.build_yaml(
        {"grp0": {"parent": ""}},
        {"slurm_control_node_x86_64": {"grp0"}},
        None,
        "slurm_cluster",
        categories,
    )
    rendered = yaml.safe_load(
        generate_functional_groups.render_yaml_with_comments(generated)
    )
    assert rendered["functional_groups"][0]["category"] == "slurm"
    assert rendered["functional_groups"][0]["layer"] == "management"


def test_slurm_render_preserves_array_key_position():
    """ORCH_UT_056: Slurm dictionaries render valid scalar/list/array lines."""
    rendered = slurm_conf.read_dict2ini({
        "ClusterName": "omnia",
        "Prolog": ["/opt/a", "/opt/b"],
        "NodeName": [{"NodeName": "node01", "CPUs": 32}],
    })
    assert rendered == [
        "ClusterName=omnia",
        "Prolog=/opt/a",
        "Prolog=/opt/b",
        "NodeName=node01 CPUs=32",
    ]


def test_slurm_merge_deduplicates_list_and_csv_values():
    """ORCH_UT_057: Slurm merge is ordered, unique, and last-writer wins."""
    merged = slurm_conf.slurm_conf_dict_merge(
        [
            {
                "ClusterName": "old",
                "Prolog": ["/opt/a", "/opt/b"],
                "GresTypes": "gpu,mps",
            },
            {
                "ClusterName": "omnia",
                "Prolog": ["/opt/b", "/opt/c"],
                "GresTypes": "gpu,shard",
            },
        ],
        "slurm",
        False,
    )
    assert merged["ClusterName"] == "omnia"
    assert merged["Prolog"] == ["/opt/a", "/opt/b", "/opt/c"]
    assert merged["GresTypes"] == "gpu,mps,shard"


class _ModuleRecorder:
    """Minimal AnsibleModule test double for file-transform helpers."""

    def __init__(self):
        self.result = None

    def exit_json(self, **kwargs):
        """Record a successful module result."""
        self.result = kwargs

    def fail_json(self, **kwargs):
        """Expose an Ansible module failure as a test assertion."""
        raise AssertionError(kwargs.get("msg", "module failed"))


def test_xname_generation_is_deterministic_across_slot_boundaries(tmp_path):
    """ORCH_UT_058: PXE rows receive stable and unique xnames."""
    mapping = tmp_path / "pxe_mapping_file.csv"
    with mapping.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["HOSTNAME", "XNAME"])
        writer.writeheader()
        for index in range(11):
            writer.writerow({"HOSTNAME": f"node{index:02d}", "XNAME": "stale"})
    module = _ModuleRecorder()
    generate_xname_in_mapping_file.generate_xname_in_mapping_file(
        str(mapping), module
    )
    with mapping.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    xnames = [row["XNAME"] for row in rows]
    assert xnames[0] == "x1000c0s0b0n0"
    assert xnames[10] == "x1000c0s1b0n0"
    assert len(xnames) == len(set(xnames))
    assert module.result and not module.result["changed"]


def test_system_environment_helpers_fail_closed(monkeypatch, tmp_path):
    """ORCH_UT_059: Environment checks reject malformed or absent values."""
    monkeypatch.delenv("OMNIA_TEST_REQUIRED", raising=False)
    assert not validate_system_environment._check_env_var(  # pylint: disable=protected-access
        "OMNIA_TEST_REQUIRED"
    )["passed"]
    assert not validate_system_environment._check_ip_on_nic(  # pylint: disable=protected-access
        "999.1.1.1"
    )["passed"]
    assert validate_system_environment._check_data_path(  # pylint: disable=protected-access
        str(tmp_path / "omnia")
    )["passed"]


def test_gpu_job_result_requires_completed_workload(monkeypatch):
    """ORCH_UT_060: GPU jobs pass only after synchronous workload output."""
    monkeypatch.setattr(
        slurm_func, "check_gpu_available",
        lambda _host: {"success": True, "skipped": False},
    )
    monkeypatch.setattr(slurm_func, "get_slurm_control_nodes", lambda _host: ["ctl"])
    monkeypatch.setattr(
        slurm_func, "get_node_ip_from_pxe_mapping",
        lambda _host, _node: "192.0.2.10",
    )
    monkeypatch.setattr(
        slurm_func, "run_ssh_command",
        lambda *_args, **_kwargs: SimpleNamespace(
            rc=0, stdout="GPU 0: NVIDIA H100\n", stderr=""
        ),
    )
    assert slurm_func.check_gpu_job_execution(object())["success"]
    monkeypatch.setattr(
        slurm_func, "run_ssh_command",
        lambda *_args, **_kwargs: SimpleNamespace(
            rc=1, stdout="", stderr="allocation failed"
        ),
    )
    assert not slurm_func.check_gpu_job_execution(object())["success"]


def test_mpi_job_result_requires_two_completed_ranks(monkeypatch):
    """ORCH_UT_061: MPI jobs pass only after compile and two-rank execution."""
    monkeypatch.setattr(
        slurm_func, "check_mpi_available",
        lambda _host: {"success": True, "skipped": False},
    )
    monkeypatch.setattr(
        slurm_func, "get_login_compiler_nodes", lambda _host: ["compiler"]
    )
    monkeypatch.setattr(
        slurm_func, "get_node_ip_from_pxe_mapping",
        lambda _host, _node: "192.0.2.20",
    )
    monkeypatch.setattr(
        slurm_func, "run_ssh_command",
        lambda *_args, **_kwargs: SimpleNamespace(
            rc=0,
            stdout="Hello from rank 0 of 2\nHello from rank 1 of 2\n",
            stderr="",
        ),
    )
    assert slurm_func.check_mpi_job_execution(object())["success"]
    monkeypatch.setattr(
        slurm_func, "run_ssh_command",
        lambda *_args, **_kwargs: SimpleNamespace(
            rc=0, stdout="Hello from rank 0 of 1\n", stderr=""
        ),
    )
    assert not slurm_func.check_mpi_job_execution(object())["success"]


def test_dataset_sync_overlays_a_complete_source_input(monkeypatch, tmp_path):
    """ORCH_UT_062: Dataset sync overlays overrides on all source inputs."""
    repository = tmp_path / "omnia"
    module_root = repository / "test" / "orchestrator"
    source_input = repository / "src" / "orchestrator" / "input"
    dataset_input = module_root / "datasets" / "selected" / "input"
    source_input.mkdir(parents=True)
    dataset_input.mkdir(parents=True)
    (source_input / "orchestrator_config.yml").write_text(
        "source: true\n", encoding="utf-8"
    )
    (source_input / "omnia_config.yml").write_text(
        "required: true\n", encoding="utf-8"
    )
    (dataset_input / "orchestrator_config.yml").write_text(
        "dataset: true\n", encoding="utf-8"
    )
    captured = {}

    def fake_sync_files(**kwargs):
        staged = kwargs["src"]
        with open(
            f"{staged}/orchestrator_config.yml", encoding="utf-8"
        ) as stream:
            captured["orchestrator"] = stream.read()
        with open(f"{staged}/omnia_config.yml", encoding="utf-8") as stream:
            captured["omnia"] = stream.read()
        return {"success": True, "details": "staged", "error": ""}

    monkeypatch.setattr(host_func, "get_module_root", lambda: str(module_root))
    monkeypatch.setattr(
        host_func, "DATASETS_DIR", str(module_root / "datasets")
    )
    monkeypatch.setattr(host_func, "SRC_INPUT_DIR", str(source_input))
    monkeypatch.setattr(
        host_func,
        "connection_params",
        lambda: {
            "mode": "local",
            "ip": "",
            "user": "root",
            "port": 22,
            "auth_secret": "",
            "ssh_opts": [],
        },
    )
    monkeypatch.setattr(host_func, "sync_files", fake_sync_files)

    result = host_func.sync_orchestrator_input(
        object(), {"dataset": "selected", "project_name": "project_default"}
    )
    assert result["success"]
    assert captured == {
        "orchestrator": "dataset: true\n",
        "omnia": "required: true\n",
    }
