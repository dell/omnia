# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Source contracts for the Orchestrator validation harness."""

import ast
from collections import defaultdict
import re

import pytest
import yaml
from omnia_auto.functions.validation_runner import ValidationRunner

from library.messages.slurm_msgs import TEST_LOG_MSGS as SLURM_LOG_MESSAGES
from ut.source_loader import REPOSITORY_ROOT, TEST_ROOT


pytestmark = pytest.mark.unit
SUPPORTED_COMMANDS = {"exec", "verify", "test"}
DOMAIN_VARS = TEST_ROOT / "library" / "vars" / "domain_vars.py"


def _literal_assignment(name):
    tree = ast.parse(DOMAIN_VARS.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) == name:
            return ast.literal_eval(node.value)
    raise AssertionError(f"Missing domain variable: {name}")


def _batch_config():
    return yaml.safe_load(
        (TEST_ROOT / "test_run_config.yml").read_text(encoding="utf-8")
    )


def _registered_markers():
    tree = ast.parse((TEST_ROOT / "conftest.py").read_text(encoding="utf-8"))
    configure = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "pytest_configure"
    )
    marker_dict = next(
        node.value for node in ast.walk(configure)
        if isinstance(node, ast.Assign)
        and any(getattr(target, "id", "") == "markers" for target in node.targets)
    )
    return set(ast.literal_eval(marker_dict))


def _has_marker(function, marker):
    return any(
        isinstance(decorator, ast.Attribute)
        and decorator.attr == marker
        and isinstance(decorator.value, ast.Attribute)
        and decorator.value.attr == "mark"
        for decorator in function.decorator_list
    )


def _has_deploy_test(path):
    for test_file in path.rglob("test_*.py"):
        tree = ast.parse(test_file.read_text(encoding="utf-8"))
        if any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
            and _has_marker(node, "deploy")
            for node in ast.walk(tree)
        ):
            return True
    return False


def test_fvt_registry_exactly_matches_real_directories():
    """ORCH_UT_037: Every real FVT tag is reachable and no phantom tag exists."""
    registered = set(_literal_assignment("FVT_TAGS"))
    actual = {
        path.name
        for path in (TEST_ROOT / "fvt").iterdir()
        if path.is_dir() and path.name != "__pycache__"
    }
    assert registered == actual


def test_declared_suites_are_real_immediate_directories():
    """ORCH_UT_038: Every advertised suite resolves inside its owning tag."""
    for tag, suites in _literal_assignment("SUITES").items():
        for suite in suites:
            suite_path = TEST_ROOT / "fvt" / tag / suite
            assert suite_path.is_dir(), str(suite_path)
            assert suite_path.parent == TEST_ROOT / "fvt" / tag


def test_batch_scenarios_exactly_match_registered_tags():
    """ORCH_UT_039: Batch configuration cannot silently omit a scenario."""
    assert set(_batch_config()["fvt_orchestrator"]) == set(
        _literal_assignment("FVT_TAGS")
    )


def test_batch_uses_only_supported_categories_and_commands():
    """ORCH_UT_040: Batch keys and commands match ValidationRunner vocabulary."""
    config = _batch_config()
    category_keys = {key for key in config if key.endswith("_orchestrator")}
    assert category_keys == {
        "fvt_orchestrator",
        "nft_orchestrator",
        "ut_orchestrator",
    }
    commands = {
        scenario["command"]
        for scenario in config["fvt_orchestrator"].values()
    }
    commands.update(
        {
            config["nft_orchestrator"]["command"],
            config["ut_orchestrator"]["command"],
        }
    )
    assert commands <= SUPPORTED_COMMANDS


def test_marker_registry_and_batch_filters_cannot_drift():
    """ORCH_UT_049: Markers exposed by config, pytest, and batch stay aligned."""
    configured = set(_literal_assignment("MARKERS"))
    assert _registered_markers() - {"order(n)"} == configured
    marker_values = [
        scenario.get("marker", "")
        for scenario in _batch_config()["fvt_orchestrator"].values()
    ]
    marker_values.extend([
        _batch_config()["nft_orchestrator"].get("marker", ""),
        _batch_config()["ut_orchestrator"].get("marker", ""),
    ])
    selected = {
        marker
        for expression in marker_values
        for marker in re.split(r"[+,]", expression)
        if marker
    }
    assert selected <= configured


def test_every_batch_full_flow_has_one_deploy_owner():
    """ORCH_UT_041: Every configured test flow has a deployment trigger."""
    for tag, scenario in _batch_config()["fvt_orchestrator"].items():
        if scenario["command"] != "test":
            continue
        target = TEST_ROOT / "fvt" / tag
        deploy_scope = target
        if scenario.get("suite") and not any(target.glob("test_*.py")):
            deploy_scope = target / scenario["suite"]
        assert _has_deploy_test(deploy_scope), str(deploy_scope)


@pytest.mark.parametrize(
    ("relative_path", "tag"),
    [
        ("precheck/test_playbook.py", "precheck"),
        ("validate/test_playbook.py", "validate"),
        ("prepare/test_playbook.py", "prepare"),
        ("deploy/test_playbook.py", "deploy"),
        ("provision/test_playbook.py", "provision"),
        ("execute/test_playbook.py", "execute"),
        ("cleanup/test_playbook.py", "cleanup"),
        ("pxeboot/test_playbook.py", "pxeboot"),
        ("rollback/test_playbook.py", "rollback"),
    ],
)
def test_lifecycle_deploy_trigger_uses_selected_public_tag(relative_path, tag):
    """ORCH_UT_051: Each lifecycle deploy trigger executes its selected tag."""
    source = (TEST_ROOT / "fvt" / relative_path).read_text(encoding="utf-8")
    assert f'run_playbook(tag="{tag}"' in source


def test_untagged_lifecycle_is_explicit_and_non_destructive():
    """ORCH_UT_042: Full test follows the public safe lifecycle order."""
    lifecycle = _literal_assignment("ALL_EXEC_TAGS")
    assert lifecycle == ["precheck", "prepare", "execute"]
    assert set(lifecycle).isdisjoint(_literal_assignment("EXCLUDE_TAGS"))
    for tag in lifecycle:
        assert _has_deploy_test(TEST_ROOT / "fvt" / tag), tag


def test_verify_only_tags_have_no_deploy_tests():
    """ORCH_UT_043: Verification-only areas cannot mutate infrastructure."""
    for tag in _literal_assignment("VERIFY_ONLY_TAGS"):
        assert not _has_deploy_test(TEST_ROOT / "fvt" / tag), tag
        assert _batch_config()["fvt_orchestrator"][tag]["command"] == "verify"


def test_entrypoint_forwards_complete_runner_contract():
    """ORCH_UT_044: Domain lifecycle controls reach the shared runner."""
    source = (TEST_ROOT / "_run.py").read_text(encoding="utf-8")
    for key in (
        "all_exec_tags",
        "all_exec_marker",
        "all_verify_exclude_markers",
        "required_suite_tags",
        "verify_only_tags",
        "verify_only_suites",
        "suite_exec_owners",
    ):
        assert f'"{key}"' in source


def test_platform_provision_suites_own_their_deploy_trigger():
    """ORCH_UT_082: K8s and Slurm suite selection executes one platform owner."""
    owners = _literal_assignment("SUITE_EXEC_OWNERS")
    assert owners == {"provision": ["kubernetes", "slurm"]}
    for suite in owners["provision"]:
        suite_path = TEST_ROOT / "fvt" / "provision" / suite
        assert _has_deploy_test(suite_path), str(suite_path)

    runner_source = (
        REPOSITORY_ROOT
        / "test/plugins/omnia_auto/functions/validation_runner.py"
    ).read_text(encoding="utf-8")
    assert "self._suite_exec_owners" in runner_source
    assert "if suite in suite_owners:" in runner_source


def test_suite_exec_owner_selection_is_scoped_and_backward_compatible(
    monkeypatch, tmp_path,
):
    """ORCH_UT_083: Platform owners do not duplicate the generic lifecycle run."""
    module_root = tmp_path / "module"
    tag_root = module_root / "fvt" / "provision"
    suite_root = tag_root / "slurm"
    suite_root.mkdir(parents=True)
    root_test = tag_root / "test_playbook.py"
    root_test.write_text("def test_root(): pass\n", encoding="utf-8")
    (suite_root / "test_slurm.py").write_text(
        "def test_slurm(): pass\n", encoding="utf-8"
    )

    calls = []
    owner_runner = ValidationRunner(
        domain="orchestrator",
        script_dir=str(module_root),
        domain_config={
            "tags": ["provision"],
            "suites": {"provision": ["slurm"]},
            "suite_exec_owners": {"provision": ["slurm"]},
        },
    )
    monkeypatch.setattr(
        owner_runner,
        "_invoke_pytest_with_summary",
        lambda path, *_args: calls.append(path) or 0,
    )
    assert owner_runner._run_exec("provision", "slurm", "", "") == 0
    assert calls == [str(suite_root.resolve())]

    calls.clear()
    legacy_runner = ValidationRunner(
        domain="another_module",
        script_dir=str(module_root),
        domain_config={
            "tags": ["provision"],
            "suites": {"provision": ["slurm"]},
        },
    )
    monkeypatch.setattr(
        legacy_runner,
        "_invoke_pytest_with_summary",
        lambda path, *_args: calls.append(path) or 0,
    )
    assert legacy_runner._run_exec("provision", "slurm", "", "") == 0
    assert calls == [[str(root_test), str(suite_root.resolve())]]


def test_slurm_batch_flow_mirrors_kubernetes_suite_layout():
    """ORCH_UT_084: Slurm deploys by provision suite and verifies by check suite."""
    config = _batch_config()["fvt_orchestrator"]
    assert config["provision"] == {
        "run": False,
        "command": "exec",
        "suite": "slurm",
        "marker": "",
        "dataset": "slurm_only",
        "sync_input": True,
        "sync_output": True,
        "sync_image_output": True,
    }
    assert config["check"]["command"] == "verify"
    assert config["check"]["suite"] == "slurm"
    assert config["check"]["dataset"] == "slurm_only"
    expected_features = {
        "additional_cloud_init",
        "apptainer",
        "gpu",
        "hpc_benchmarks",
        "platform",
        "powervault",
        "vast",
    }
    slurm_check = TEST_ROOT / "fvt" / "check" / "slurm"
    assert expected_features <= {
        path.name for path in slurm_check.iterdir() if path.is_dir()
    }


def test_runner_selected_deploy_and_nft_are_not_auto_skipped():
    """ORCH_UT_045: Runner command type, not an unrelated option, enables phases."""
    source = (TEST_ROOT / "conftest.py").read_text(encoding="utf-8")
    assert 'command_type != "exec"' in source
    assert 'command_type != "nft"' in source
    assert 'command_type == "exec" and _item_has_marker(item, "deploy")' in source
    assert "use --marker deploy to enable" not in source
    assert "--marker nft to enable" not in source


def test_destructive_flows_require_explicit_marker():
    """ORCH_UT_046: Cleanup, PXE and rollback cannot run accidentally."""
    entrypoint = (TEST_ROOT / "_run.py").read_text(encoding="utf-8")
    assert {"cleanup", "pxeboot", "rollback"} <= set(
        ast.literal_eval(
            next(
                node.value
                for node in ast.parse(entrypoint).body
                if isinstance(node, ast.Assign)
                and any(getattr(target, "id", "") == "_DESTRUCTIVE_TAGS" for target in node.targets)
            )
        )
    )
    for tag in ("cleanup", "pxeboot", "rollback"):
        scenario = _batch_config()["fvt_orchestrator"][tag]
        assert scenario["marker"] == "destructive"
        for test_file in (TEST_ROOT / "fvt" / tag).rglob("test_*.py"):
            assert "pytestmark = pytest.mark.destructive" in test_file.read_text(
                encoding="utf-8"
            ), str(test_file)


def test_state_changing_nft_cases_are_explicitly_destructive():
    """ORCH_UT_050: Broad NFT runs cannot prepare, provision, or clean hosts."""
    expected = {
        "nft/test_idempotency.py": {
            "test_prepare_idempotent",
            "test_cleanup_idempotent",
        },
        "nft/test_performance.py": {
            "test_prepare_performance",
            "test_provision_performance",
            "test_cleanup_performance",
        },
    }
    for relative_path, function_names in expected.items():
        tree = ast.parse((TEST_ROOT / relative_path).read_text(encoding="utf-8"))
        functions = {
            node.name: node for node in tree.body
            if isinstance(node, ast.FunctionDef)
        }
        for function_name in function_names:
            assert _has_marker(functions[function_name], "destructive"), (
                f"{relative_path}::{function_name} is not protected"
            )
    conftest = (TEST_ROOT / "conftest.py").read_text(encoding="utf-8")
    assert 'if "destructive" not in markers:' in conftest


def test_all_test_case_ids_are_present_and_unique():
    """ORCH_UT_047: Every test has one unique, convention-compliant ID."""
    occurrences = defaultdict(list)
    missing = []
    invalid = []
    pattern = re.compile(
        r"\b(?:ORCH_FVT_[A-Z0-9_]+_[EV]\d{3}|ORCH_NFT_\d{3}|"
        r"ORCH_UT_\d{3}|TC_K8_\d{3})\b"
    )
    expected_patterns = {
        "fvt": re.compile(r"ORCH_FVT_[A-Z0-9_]+_[EV]\d{3}"),
        "nft": re.compile(r"ORCH_NFT_\d{3}"),
        "ut": re.compile(r"ORCH_UT_\d{3}"),
    }
    for area in ("fvt", "nft", "ut"):
        root = TEST_ROOT / area
        for test_file in root.rglob("test_*.py"):
            tree = ast.parse(test_file.read_text(encoding="utf-8"))
            for function in (
                node for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name.startswith("test_")
            ):
                ids = pattern.findall(ast.get_docstring(function) or "")
                if len(ids) != 1:
                    missing.append(f"{test_file.relative_to(TEST_ROOT)}::{function.name}")
                    continue
                relative_path = test_file.relative_to(TEST_ROOT)
                is_kubernetes = area == "fvt" and "kubernetes" in relative_path.parts
                expected = (
                    re.compile(r"TC_K8_\d{3}")
                    if is_kubernetes
                    else expected_patterns[area]
                )
                if not expected.fullmatch(ids[0]):
                    invalid.append(
                        f"{relative_path}::{function.name}={ids[0]}"
                    )
                occurrences[ids[0]].append(
                    f"{test_file.relative_to(REPOSITORY_ROOT)}::{function.name}"
                )
    duplicates = {key: value for key, value in occurrences.items() if len(value) > 1}
    sequences = defaultdict(set)
    for test_case_id in occurrences:
        fvt_match = re.fullmatch(
            r"ORCH_FVT_([A-Z0-9_]+)_([EV])(\d{3})", test_case_id
        )
        generic_match = re.fullmatch(r"ORCH_(NFT|UT)_(\d{3})", test_case_id)
        if fvt_match:
            sequences[
                f"ORCH_FVT_{fvt_match.group(1)}_{fvt_match.group(2)}"
            ].add(int(fvt_match.group(3)))
        elif generic_match:
            sequences[f"ORCH_{generic_match.group(1)}"].add(
                int(generic_match.group(2))
            )
    sequence_gaps = {
        family: sorted(set(range(1, max(numbers) + 1)) - numbers)
        for family, numbers in sequences.items()
        if numbers and set(range(1, max(numbers) + 1)) != numbers
    }
    assert not missing, f"Tests without exactly one docstring ID: {missing}"
    assert not invalid, f"Tests with invalid test-case IDs: {invalid}"
    assert not duplicates, f"Duplicate test-case IDs: {duplicates}"
    assert not sequence_gaps, f"Test-case ID sequences contain gaps: {sequence_gaps}"


def test_report_payload_includes_test_case_id():
    """ORCH_UT_048: HTML/session reporting preserves the test identity."""
    source = (TEST_ROOT / "conftest.py").read_text(encoding="utf-8")
    assert '"tc_id": tc_id' in source


def test_live_verifiers_use_runtime_safe_contracts():
    """ORCH_UT_095: Live checks use valid messages, endpoints and feature gates."""
    advanced_path = (
        TEST_ROOT / "fvt" / "check" / "slurm" / "test_slurm_advanced.py"
    )
    advanced_source = advanced_path.read_text(encoding="utf-8")
    advanced_tree = ast.parse(advanced_source)
    referenced_log_keys = {
        node.slice.value
        for node in ast.walk(advanced_tree)
        if isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == "LOG"
        and isinstance(node.slice, ast.Constant)
        and isinstance(node.slice.value, str)
    }
    assert referenced_log_keys <= set(SLURM_LOG_MESSAGES)

    optional_check_calls = sum(
        1
        for node in ast.walk(advanced_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "skip_if_not_applicable"
    )
    assert optional_check_calls == 14

    orchestrator_source = (
        TEST_ROOT / "library" / "functions" / "orchestrator_func.py"
    ).read_text(encoding="utf-8")
    assert 'readiness_path = "/hsm/v2/service/ready"' in orchestrator_source
    assert 'CMDS["hostname_fqdn"]' in orchestrator_source
    assert 'host="localhost"' not in orchestrator_source

    slurm_source = (
        TEST_ROOT / "library" / "functions" / "slurm_func.py"
    ).read_text(encoding="utf-8")
    assert "sinfo -h -o '%N|%G'" in slurm_source
    assert 'normalized_gres not in {"", "(null)", "n/a"}' in slurm_source
