# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Broad deterministic source-structure checks for Orchestrator."""

import ast
import json
from pathlib import Path

import pytest
import yaml

from ut.source_loader import ORCHESTRATOR_ROOT
from library.vars.common_vars import PLAYBOOK_TAGS


pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "source_file",
    sorted(ORCHESTRATOR_ROOT.rglob("*.py")),
    ids=lambda path: str(path.relative_to(ORCHESTRATOR_ROOT)),
)
def test_all_python_sources_parse(source_file):
    """ORCH_UT_064: Every Orchestrator Python source parses."""
    ast.parse(source_file.read_text(encoding="utf-8"), filename=str(source_file))


@pytest.mark.parametrize(
    "schema_file",
    sorted(ORCHESTRATOR_ROOT.rglob("*.json")),
    ids=lambda path: str(path.relative_to(ORCHESTRATOR_ROOT)),
)
def test_all_json_contracts_parse(schema_file):
    """ORCH_UT_065: Every Orchestrator JSON contract parses."""
    json.loads(schema_file.read_text(encoding="utf-8"))


def test_every_role_has_an_executable_entrypoint():
    """ORCH_UT_066: Every role exposes tasks/main.yml."""
    roles = sorted(path for path in (ORCHESTRATOR_ROOT / "roles").iterdir() if path.is_dir())
    assert roles
    missing = [role.name for role in roles if not (role / "tasks" / "main.yml").is_file()]
    assert not missing, f"Roles without tasks/main.yml: {missing}"


def test_all_playbook_imports_resolve_inside_collection():
    """ORCH_UT_067: Imported playbooks resolve to real collection files."""
    playbook_root = ORCHESTRATOR_ROOT / "playbooks"
    missing = []
    for playbook in playbook_root.rglob("*.yml"):
        try:
            data = yaml.safe_load(playbook.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if not isinstance(data, list):
            continue
        for play in data:
            if not isinstance(play, dict):
                continue
            imported = play.get("ansible.builtin.import_playbook") or play.get("import_playbook")
            if not isinstance(imported, str) or "{{" in imported:
                continue
            target = (playbook.parent / imported).resolve()
            if not target.is_file() or playbook_root.resolve() not in target.parents:
                missing.append(f"{playbook.relative_to(playbook_root)} -> {imported}")
    assert not missing, f"Unresolved playbook imports: {missing}"


def test_custom_modules_publish_an_executable_contract():
    """ORCH_UT_068: Every custom module is documented and executable."""
    failures = []
    for module in sorted((ORCHESTRATOR_ROOT / "plugins" / "modules").glob("*.py")):
        tree = ast.parse(module.read_text(encoding="utf-8"))
        functions = {
            node.name for node in tree.body if isinstance(node, ast.FunctionDef)
        }
        assignments = {
            target.id
            for node in tree.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }
        documented = bool(ast.get_docstring(tree) or "DOCUMENTATION" in assignments)
        executable = bool({"main", "run_module"} & functions)
        if not documented or not executable:
            failures.append(module.name)
    assert not failures, (
        "Modules without a documented main/run_module entrypoint: "
        f"{failures}"
    )


def test_public_orchestrator_tags_match_documented_contract():
    """ORCH_UT_069: Public lifecycle tags cannot drift unnoticed."""
    expected = {
        "always",
        "precheck",
        "validate",
        "credentials",
        "prepare",
        "deploy",
        "provision",
        "execute",
        "validate-deployment",
        "pxeboot",
        "cleanup",
        "cleanup_credentials",
        "upgrade",
        "rollback",
        "never",
    }
    playbook = yaml.safe_load(
        (ORCHESTRATOR_ROOT / "playbooks" / "orchestrator.yml").read_text(
            encoding="utf-8"
        )
    )
    tags = set()
    for play in playbook:
        value = play.get("tags", [])
        tags.update([value] if isinstance(value, str) else value)
    assert tags == expected
    assert set(PLAYBOOK_TAGS) == expected


def test_no_playbook_uses_an_absolute_local_import():
    """ORCH_UT_070: Playbooks remain relocatable across controller paths."""
    offenders = []
    for playbook in (ORCHESTRATOR_ROOT / "playbooks").rglob("*.yml"):
        text = playbook.read_text(encoding="utf-8")
        if "import_playbook: /" in text:
            offenders.append(str(playbook.relative_to(ORCHESTRATOR_ROOT)))
    assert not offenders, offenders
