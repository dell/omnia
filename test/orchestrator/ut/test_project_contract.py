# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Contracts for custom Orchestrator project selection."""

from pathlib import Path

import pytest

from library.functions.project_func import (
    resolve_input_project_path,
    resolve_output_project_path,
    resolve_project_name,
)
from ut.source_loader import TEST_ROOT


pytestmark = pytest.mark.unit


def test_custom_project_resolves_input_and_output_from_environment(monkeypatch):
    """ORCH_UT_110: Runtime environment controls project paths."""
    monkeypatch.setenv("OMNIA_PROJECT_NAME", "nightly_slurm")
    monkeypatch.setenv("ORCHESTRATOR_DATA_PATH", "/srv/omnia/orchestrator")
    monkeypatch.setenv("OMNIA_DATA_PATH", "/ignored")
    assert resolve_project_name() == "nightly_slurm"
    assert resolve_input_project_path() == (
        "/srv/omnia/orchestrator/input/nightly_slurm"
    )
    assert resolve_output_project_path() == (
        "/srv/omnia/orchestrator/output/nightly_slurm"
    )


@pytest.mark.parametrize(
    "project_name",
    ("../escape", "/absolute", "space project", ".", "..", ""),
)
def test_unsafe_project_names_fail_closed(monkeypatch, project_name):
    """ORCH_UT_111: Project selection cannot escape runtime roots."""
    monkeypatch.setenv("OMNIA_PROJECT_NAME", project_name)
    with pytest.raises(ValueError, match="Unsafe project_name"):
        resolve_project_name()


def test_omnia_data_path_fallback_is_used(monkeypatch):
    """ORCH_UT_112: Domain root falls back below OMNIA_DATA_PATH."""
    monkeypatch.delenv("ORCHESTRATOR_DATA_PATH", raising=False)
    monkeypatch.setenv("OMNIA_DATA_PATH", "/srv/omnia")
    monkeypatch.setenv("OMNIA_PROJECT_NAME", "project_alpha")
    assert resolve_input_project_path() == (
        "/srv/omnia/orchestrator/input/project_alpha"
    )


def test_non_kubernetes_entrypoints_have_no_default_project_paths():
    """ORCH_UT_113: Project-aware entry points contain no fixed project path."""
    entrypoints = (
        TEST_ROOT / "fvt" / "precheck" / "test_connectivity.py",
        TEST_ROOT / "fvt" / "pxeboot" / "test_pxeboot.py",
        TEST_ROOT
        / "fvt"
        / "check"
        / "slurm"
        / "platform"
        / "test_module_contract.py",
        TEST_ROOT / "library" / "functions" / "orchestrator_module_tester.py",
        TEST_ROOT / "nft" / "test_permissions.py",
    )
    forbidden = (
        "/input/project_default",
        "/output/project_default",
    )
    for entrypoint in entrypoints:
        source = Path(entrypoint).read_text(encoding="utf-8")
        assert not any(value in source for value in forbidden), entrypoint


def test_setup_env_uses_runtime_project_for_credentials():
    """ORCH_UT_114: Credential setup follows the Omnia environment."""
    source = (TEST_ROOT / "setup_env.sh").read_text(encoding="utf-8")
    assert "_configured_project_name" not in source
    assert "OMNIA_PROJECT_NAME" in source
