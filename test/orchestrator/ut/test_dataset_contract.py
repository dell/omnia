# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Consumer contracts for the dataset implementation supplied by PR #5220."""

import os
import json
import importlib.util
import subprocess
import sys

from jsonschema import Draft7Validator
import pytest
import yaml

import conftest as orchestrator_conftest
from library.functions import host_func, validation_func
from ut.source_loader import ORCHESTRATOR_ROOT, TEST_ROOT


pytestmark = pytest.mark.unit
DATASETS_ROOT = TEST_ROOT / "datasets"
GENERATOR = DATASETS_ROOT / "generator" / "generate_dataset.py"
PROFILES_ROOT = DATASETS_ROOT / "generator" / "profiles"
SCHEMA_ROOT = (
    ORCHESTRATOR_ROOT
    / "plugins"
    / "module_utils"
    / "orchestrator_validation"
    / "schema"
)


def _yaml(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _base_config():
    return {
        "oim_server_ip": "",
        "clone_path": "/root/omnia",
        "project_name": "project_default",
        "report_path": "/opt/omnia/reports",
        "report_name": "orchestrator_test_report",
        "dataset": "",
        "sync_orchestrator_input": False,
        "sync_repo_manager_output": False,
        "sync_image_build_manager_output": False,
    }


def _generator_module():
    spec = importlib.util.spec_from_file_location(
        "orchestrator_dataset_generator", GENERATOR
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_profiles_reference_complete_source_artifacts():
    """ORCH_UT_001: Profiles reference existing input and upstream handoff files."""
    source_inputs = ORCHESTRATOR_ROOT / "input"
    expected_samples = {"repo_manager_output", "image_build_manager_output"}
    for profile_name in ("slurm_only", "k8s_only", "k8s_and_slurm"):
        profile = _yaml(PROFILES_ROOT / f"{profile_name}.yml")
        includes = profile["include_files"]
        assert includes["input"]
        assert all((source_inputs / name).is_file() for name in includes["input"])
        assert set(includes["samples"]) == expected_samples
        assert all(
            (ORCHESTRATOR_ROOT / "samples" / name).is_dir()
            for name in includes["samples"]
        )


def test_slurm_profile_dry_run_generates_without_publishing():
    """ORCH_UT_002: Slurm dataset generation validates all files without publishing."""
    dataset_name = "unit_slurm_contract"
    output = DATASETS_ROOT / dataset_name
    assert not output.exists()
    result = subprocess.run(
        [sys.executable, str(GENERATOR), dataset_name, "slurm_only", "--dry-run"],
        cwd=str(TEST_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Dry run passed" in result.stdout
    assert not output.exists()


def test_generator_lists_every_supported_profile():
    """ORCH_UT_003: Dataset generator advertises all supported deployment profiles."""
    result = subprocess.run(
        [sys.executable, str(GENERATOR), "--list-profiles"],
        cwd=str(TEST_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    for profile in ("defaults", "slurm_only", "k8s_only", "k8s_and_slurm"):
        assert profile in result.stdout


def test_generator_rejects_an_unknown_profile_without_publishing():
    """ORCH_UT_004: Unknown dataset profiles fail without publishing a dataset."""
    dataset_name = "unit_unknown_profile"
    output = DATASETS_ROOT / dataset_name
    result = subprocess.run(
        [sys.executable, str(GENERATOR), dataset_name, "does_not_exist", "--dry-run"],
        cwd=str(TEST_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert not output.exists()


def test_empty_dataset_uses_current_source_fallbacks(monkeypatch):
    """ORCH_UT_005: Empty dataset mode resolves canonical source inputs and outputs."""
    monkeypatch.delenv("OMNIA_DATASET_OVERRIDE", raising=False)
    monkeypatch.setattr(validation_func, "load_test_config", _base_config)
    result = validation_func.validate_test_config()
    assert result["valid"], result["errors"]
    assert host_func._resolve_dataset_subdir(  # pylint: disable=protected-access
        {"dataset": ""}, "input", host_func.SRC_INPUT_DIR
    ) == os.path.realpath(host_func.SRC_INPUT_DIR)


def test_named_dataset_subdirectory_resolves_inside_dataset_root(
    monkeypatch, tmp_path
):
    """ORCH_UT_006: Named datasets resolve only below the configured dataset root."""
    dataset_root = tmp_path / "datasets"
    input_dir = dataset_root / "slurm_case" / "input"
    input_dir.mkdir(parents=True)
    monkeypatch.setattr(host_func, "DATASETS_DIR", str(dataset_root))
    resolved = host_func._resolve_dataset_subdir(  # pylint: disable=protected-access
        {"dataset": "slurm_case"}, "input", host_func.SRC_INPUT_DIR
    )
    assert resolved == str(input_dir.resolve())


def test_dataset_path_traversal_is_rejected():
    """ORCH_UT_007: Dataset consumers reject path traversal selections."""
    with pytest.raises(ValueError, match="Unsafe dataset name"):
        host_func._resolve_dataset_subdir(  # pylint: disable=protected-access
            {"dataset": "../outside"}, "input", host_func.SRC_INPUT_DIR
        )


def test_missing_named_dataset_fails_configuration(monkeypatch):
    """ORCH_UT_008: A missing selected dataset is a startup error, not a warning."""
    monkeypatch.setenv("OMNIA_DATASET_OVERRIDE", "missing_dataset")
    monkeypatch.setattr(validation_func, "load_test_config", _base_config)
    result = validation_func.validate_test_config()
    assert not result["valid"]
    assert any("Dataset directory not found" in error for error in result["errors"])


def test_batch_scenarios_expose_all_dataset_sync_controls():
    """ORCH_UT_009: Every FVT scenario controls input and both upstream handoffs."""
    config = _yaml(TEST_ROOT / "test_run_config.yml")
    for scenario in config["fvt_orchestrator"].values():
        for field in ("sync_input", "sync_output", "sync_image_output"):
            assert isinstance(scenario[field], bool), field


def test_dataset_overrides_reach_all_session_sync_flags(monkeypatch):
    """ORCH_UT_010: Batch overrides reach all three session synchronization legs."""
    monkeypatch.setenv("OMNIA_SYNC_INPUT_OVERRIDE", "true")
    monkeypatch.setenv("OMNIA_SYNC_OUTPUT_OVERRIDE", "true")
    monkeypatch.setenv("OMNIA_SYNC_IMAGE_OUTPUT_OVERRIDE", "true")
    resolved = orchestrator_conftest._apply_dataset_overrides({})  # pylint: disable=protected-access
    assert resolved["sync_orchestrator_input"] is True
    assert resolved["sync_repo_manager_output"] is True
    assert resolved["sync_image_build_manager_output"] is True


def test_malformed_repo_status_fails_closed(tmp_path):
    """ORCH_UT_011: Invalid Repo Manager handoff types return validation errors."""
    repo_status = tmp_path / "repo_status.yml"
    repo_status.write_text(
        "overall_status: success\ncluster_os_type: rhel\n"
        "repositories: {}\nrepo_manager: []\n",
        encoding="utf-8",
    )
    errors = validation_func._validate_repo_status(repo_status)  # pylint: disable=protected-access
    assert any("repo_manager must be a mapping" in error for error in errors)
    assert any("server_crt is missing" in error for error in errors)


def test_malformed_image_build_status_fails_closed(tmp_path):
    """ORCH_UT_012: Invalid Image Build Manager handoffs return validation errors."""
    build_status = tmp_path / "build_status.yml"
    build_status.write_text(
        "overall_status: failed\ns3_configurations: []\nfunctional_group_images: {}\n",
        encoding="utf-8",
    )
    errors = validation_func._validate_build_status(build_status)  # pylint: disable=protected-access
    assert any("not successful" in error for error in errors)
    assert any("s3_configurations must be a mapping" in error for error in errors)
    assert any("functional_group_images" in error for error in errors)


def test_generated_dataset_layout_and_manifest_are_complete(tmp_path):
    """ORCH_UT_085: Generated output has the complete PR #5220 handoff layout."""
    generator = _generator_module()
    output = tmp_path / "slurm_dataset"
    profile = _yaml(PROFILES_ROOT / "slurm_only.yml")
    rendered = generator._copy_from_src(output, profile)  # pylint: disable=protected-access
    generator._generate_readme(  # pylint: disable=protected-access
        "slurm_dataset", "slurm_only", profile, rendered, output
    )
    expected_inputs = {
        f"input/{name}" for name in profile["include_files"]["input"]
    }
    actual = {
        str(path.relative_to(output))
        for path in output.rglob("*")
        if path.is_file()
    }
    assert expected_inputs <= actual
    assert "repo_manager_output/repo_status.yml" in actual
    assert "image_build_manager_output/build_status.yml" in actual
    assert "README.md" in actual
    assert not any(path.is_symlink() for path in output.rglob("*"))


@pytest.mark.parametrize("profile_name", ("slurm_only", "k8s_only", "k8s_and_slurm"))
def test_generated_dataset_inputs_pass_current_schemas(profile_name):
    """ORCH_UT_086: Every generated profile source satisfies current input schemas."""
    profile = _yaml(PROFILES_ROOT / f"{profile_name}.yml")
    contracts = {
        "orchestrator_config.yml": "orchestrator_config.json",
        "network_spec.yml": "network_spec.json",
    }
    for input_name, schema_name in contracts.items():
        assert input_name in profile["include_files"]["input"]
        schema = json.loads((SCHEMA_ROOT / schema_name).read_text(encoding="utf-8"))
        data = _yaml(ORCHESTRATOR_ROOT / "input" / input_name)
        errors = list(Draft7Validator(schema).iter_errors(data))
        assert not errors, [error.message for error in errors]


def test_checked_in_datasets_are_reproducible(tmp_path):
    """ORCH_UT_087: Repeated PR #5220 generation produces identical artifacts."""
    generator = _generator_module()
    profile = _yaml(PROFILES_ROOT / "slurm_only.yml")
    first = tmp_path / "first"
    second = tmp_path / "second"
    generator._copy_from_src(first, profile)  # pylint: disable=protected-access
    generator._copy_from_src(second, profile)  # pylint: disable=protected-access
    first_files = {
        str(path.relative_to(first)): path.read_bytes()
        for path in first.rglob("*")
        if path.is_file()
    }
    second_files = {
        str(path.relative_to(second)): path.read_bytes()
        for path in second.rglob("*")
        if path.is_file()
    }
    assert first_files == second_files


def test_slurm_profile_has_an_explicit_behavioral_difference():
    """ORCH_UT_088: Slurm and Kubernetes profiles preserve their DCGM distinction."""
    slurm = _yaml(PROFILES_ROOT / "slurm_only.yml")
    kubernetes = _yaml(PROFILES_ROOT / "k8s_only.yml")
    assert slurm["dcgm_enabled"] is True
    assert kubernetes["dcgm_enabled"] is False
    assert slurm != kubernetes


def test_repo_status_fixtures_track_the_current_source_sample():
    """ORCH_UT_089: All platform profiles include the canonical upstream handoffs."""
    for profile_name in ("slurm_only", "k8s_only", "k8s_and_slurm"):
        profile = _yaml(PROFILES_ROOT / f"{profile_name}.yml")
        assert set(profile["include_files"]["samples"]) == {
            "repo_manager_output",
            "image_build_manager_output",
        }
    assert (
        ORCHESTRATOR_ROOT / "samples/repo_manager_output/repo_status.yml"
    ).is_file()
    assert (
        ORCHESTRATOR_ROOT / "samples/image_build_manager_output/build_status.yml"
    ).is_file()


def test_generator_rejects_unsafe_dataset_names():
    """ORCH_UT_090: Unsafe generator destinations fail without publication."""
    escaped = DATASETS_ROOT.parent / "unit_escape_contract"
    assert not escaped.exists()
    result = subprocess.run(
        [
            sys.executable,
            str(GENERATOR),
            "../unit_escape_contract",
            "slurm_only",
            "--dry-run",
        ],
        cwd=str(TEST_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert not escaped.exists()


def test_dataset_validation_fails_closed_for_missing_selection(monkeypatch):
    """ORCH_UT_091: A missing dataset override remains a startup error."""
    monkeypatch.setenv("OMNIA_DATASET_OVERRIDE", "missing_dataset")
    monkeypatch.setattr(validation_func, "load_test_config", _base_config)
    result = validation_func.validate_test_config()
    assert not result["valid"]
    assert any("Dataset directory not found" in error for error in result["errors"])


def test_batch_scenarios_expose_output_sync_control():
    """ORCH_UT_092: Every FVT batch scenario exposes both upstream sync controls."""
    config = _yaml(TEST_ROOT / "test_run_config.yml")
    for scenario in config["fvt_orchestrator"].values():
        assert isinstance(scenario["sync_output"], bool)
        assert isinstance(scenario["sync_image_output"], bool)


def test_output_override_reaches_repo_manager_sync(monkeypatch):
    """ORCH_UT_093: Repo Manager output overrides reach the session sync config."""
    monkeypatch.setenv("OMNIA_SYNC_OUTPUT_OVERRIDE", "true")
    resolved = orchestrator_conftest._apply_dataset_overrides({})  # pylint: disable=protected-access
    assert resolved["sync_repo_manager_output"] is True


def test_invalid_sync_override_fails_closed(monkeypatch):
    """ORCH_UT_094: Invalid synchronization overrides are never guessed."""
    monkeypatch.setenv("OMNIA_SYNC_INPUT_OVERRIDE", "sometimes")
    monkeypatch.setattr(validation_func, "load_test_config", _base_config)
    result = validation_func.validate_test_config()
    assert not result["valid"]
    assert any("OMNIA_SYNC_INPUT_OVERRIDE" in error for error in result["errors"])
