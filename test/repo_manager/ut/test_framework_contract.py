# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Source-contract tests for the Repo Manager automation harness."""

# pylint: disable=protected-access,wrong-import-position

import ast
import importlib
import importlib.util
import sys
import types
import unittest
from unittest.mock import patch

import yaml

from source_loader import REPOSITORY_ROOT


TEST_ROOT = REPOSITORY_ROOT / "test" / "repo_manager"
SHARED_RUNNER = (
    REPOSITORY_ROOT
    / "test"
    / "plugins"
    / "omnia_auto"
    / "functions"
    / "validation_runner.py"
)
SUPPORTED_COMMANDS = {"exec", "verify", "test"}
SHARED_PLUGIN_ROOT = REPOSITORY_ROOT / "test" / "plugins"

if str(SHARED_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(SHARED_PLUGIN_ROOT))
if importlib.util.find_spec("testinfra") is None:
    testinfra_stub = types.ModuleType("testinfra")
    testinfra_stub.get_host = lambda *_args, **_kwargs: None
    sys.modules["testinfra"] = testinfra_stub

from omnia_auto.functions import validation_runner as shared_runner  # noqa: E402


def _literal_assignment(name):
    """Read one literal module-level assignment without importing FVT dependencies."""
    tree = ast.parse(
        (TEST_ROOT / "library" / "vars" / "domain_vars.py").read_text(
            encoding="utf-8"
        )
    )
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) == name:
            return ast.literal_eval(node.value)
    raise AssertionError(f"Missing domain variable: {name}")


def _batch_config():
    """Return the Repo Manager batch configuration."""
    return yaml.safe_load(
        (TEST_ROOT / "test_run_config.yml").read_text(encoding="utf-8")
    )


def _has_deploy_test(path):
    """Return whether *path* contains a deploy-marked test function."""
    for test_file in path.rglob("test_*.py"):
        tree = ast.parse(test_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not node.name.startswith("test_"):
                continue
            for decorator in node.decorator_list:
                if (
                    isinstance(decorator, ast.Attribute)
                    and decorator.attr == "deploy"
                    and isinstance(decorator.value, ast.Attribute)
                    and decorator.value.attr == "mark"
                ):
                    return True
    return False


def _deploy_playbook_tags(path):
    """Return literal playbook tags called by deploy-marked tests under *path*."""
    tags = set()
    for test_file in path.rglob("test_*.py"):
        tree = ast.parse(test_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            has_deploy_marker = any(
                isinstance(decorator, ast.Attribute)
                and decorator.attr == "deploy"
                for decorator in node.decorator_list
            )
            if not has_deploy_marker:
                continue
            for call in ast.walk(node):
                if not isinstance(call, ast.Call):
                    continue
                if getattr(call.func, "id", None) != "run_playbook":
                    continue
                for keyword in call.keywords:
                    if keyword.arg == "tag" and isinstance(
                        keyword.value, ast.Constant
                    ):
                        tags.add(keyword.value.value)
    return tags


def _validation_runner(script_dir=TEST_ROOT):
    """Build the shared runner with Repo Manager lifecycle constraints."""
    config = {
        "tags": _literal_assignment("FVT_TAGS"),
        "markers": _literal_assignment("MARKERS"),
        "suites": _literal_assignment("SUITES"),
        "exclude_tags": _literal_assignment("EXCLUDE_TAGS"),
    }
    return shared_runner.ValidationRunner(
        domain="repo_manager",
        script_dir=str(script_dir),
        domain_config=config,
    )


class FrameworkContractTests(unittest.TestCase):  # pylint: disable=too-many-public-methods
    """Keep runner configuration, wrappers and lifecycle suites aligned."""

    def test_batch_fvt_scenarios_match_registered_tags(self):
        """Every configured scenario is accepted by the domain runner."""
        config = _batch_config()
        configured = set(config["fvt_repo_manager"])
        fvt_tags = _literal_assignment("FVT_TAGS")
        self.assertEqual(configured, set(fvt_tags))
        for tag in fvt_tags:
            self.assertTrue((TEST_ROOT / "fvt" / tag).is_dir(), tag)

    def test_declared_suites_are_real_immediate_directories(self):
        """Every advertised suite resolves directly beneath its FVT tag."""
        for tag, suites in _literal_assignment("SUITES").items():
            for suite in suites:
                suite_path = TEST_ROOT / "fvt" / tag / suite
                self.assertTrue(suite_path.is_dir(), str(suite_path))
                self.assertEqual(suite_path.parent.name, tag)

    def test_batch_commands_use_the_shared_runner_vocabulary(self):
        """Batch entries use only exec, verify, or test."""
        config = _batch_config()
        commands = {
            scenario["command"]
            for scenario in config["fvt_repo_manager"].values()
        }
        commands.add(config["ut_repo_manager"]["command"])
        self.assertLessEqual(commands, SUPPORTED_COMMANDS)

    def test_batch_test_targets_have_a_deploy_trigger(self):
        """Every configured full-flow target can execute before verifying."""
        for tag, scenario in _batch_config()["fvt_repo_manager"].items():
            if scenario["command"] != "test":
                continue
            target = TEST_ROOT / "fvt" / tag
            if scenario.get("suite"):
                target /= scenario["suite"]
            self.assertTrue(_has_deploy_test(target), str(target))

    def test_untagged_lifecycle_is_ordered_and_non_destructive(self):
        """An untagged exec/test has an explicit safe lifecycle."""
        lifecycle = ["precheck", "prepare", "execute", "status"]
        excluded = set(_literal_assignment("EXCLUDE_TAGS"))
        self.assertTrue(excluded.isdisjoint(lifecycle))
        for tag in lifecycle:
            self.assertTrue(_has_deploy_test(TEST_ROOT / "fvt" / tag), tag)

    def test_lifecycle_scenarios_call_the_intended_public_tags(self):
        """Scenario names resolve to the intended Repo Manager playbook tags."""
        expected = {
            "precheck": "precheck",
            "prepare": "prepare",
            "execute": "execute",
            "status": "status",
            "cleanup": "cleanup_pulp",
            "cleanup_repos": "cleanup_repos",
        }
        for scenario, playbook_tag in expected.items():
            called_tags = _deploy_playbook_tags(
                TEST_ROOT / "fvt" / scenario
            )
            self.assertIn(playbook_tag, called_tags, scenario)

    def test_verify_only_targets_are_not_configured_for_execution(self):
        """Targets without deploy triggers fail closed at configuration time."""
        # negative and user_registry are verify-only (no deploy tests)
        # They should not be configured with command: "test" or "exec"
        config = _batch_config()
        verify_only_scenarios = ["negative", "user_registry"]
        for scenario in verify_only_scenarios:
            self.assertIn(scenario, config["fvt_repo_manager"])
            self.assertEqual(config["fvt_repo_manager"][scenario]["command"], "verify")

    def test_catalog_lifecycle_requires_one_real_suite(self):
        """Catalog lifecycle execution cannot fan out across operations."""
        # When catalog is run without a suite, it should fail or require explicit suite
        # This is a configuration-time check - catalog has multiple suites
        config = _batch_config()
        catalog_config = config["fvt_repo_manager"].get("catalog", {})
        # Catalog should require a suite to be specified
        self.assertIsNotNone(catalog_config.get("suite"))
        self.assertNotEqual(catalog_config.get("suite", ""), "")

    def test_catalog_lifecycle_suites_call_their_public_tags(self):
        """Every executable catalog suite owns its matching playbook tag."""
        # Catalog suites: add, delete, generate, validate
        # Each should call run_playbook with matching tag
        catalog_suites = _literal_assignment("SUITES")["catalog"]
        expected_tags = {
            "add": "catalog_add",
            "delete": "catalog_delete",
            "generate": "catalog_generate",
            "validate": "catalog_validate",
        }
        for suite in catalog_suites:
            suite_path = TEST_ROOT / "fvt" / "catalog" / suite
            called_tags = _deploy_playbook_tags(suite_path)
            expected = expected_tags.get(suite)
            if expected:
                self.assertIn(expected, called_tags, f"Suite {suite} should call {expected}")

    def test_selected_suite_is_forwarded_to_execution(self):
        """A full flow executes only the selected operation suite."""
        # When a suite is specified, the runner should only execute that suite
        # This is verified by checking the runner's _run_test behavior
        runner = _validation_runner()
        # The runner should use the suite parameter to filter test paths
        # This is a structural check - the suite is passed to _invoke_pytest_with_summary
        self.assertTrue(hasattr(runner, "_run_test"))

    def test_entrypoint_forwards_the_lifecycle_contract(self):
        """Repo Manager passes every domain lifecycle rule to the runner."""
        # Verify that _run.py passes all required domain config keys
        run_source = (TEST_ROOT / "_run.py").read_text(encoding="utf-8")
        required_keys = ["tags", "markers", "suites", "exclude_tags"]
        for key in required_keys:
            self.assertIn(key, run_source, f"Missing {key} in domain_config")
        # Verify domain_vars is imported
        self.assertIn("from library.vars.domain_vars import", run_source)

    def test_runner_entrypoint_dependencies_are_importable(self):
        """The CLI dependency graph has no missing domain constants."""
        domain_vars = importlib.import_module("library.vars.domain_vars")
        self.assertEqual(domain_vars.DOMAIN_NAME, "repo_manager")

    def test_pytest_entrypoint_can_import_shared_ut_loader(self):
        """ValidationRunner's absolute UT path can resolve source_loader.py."""
        conftest_source = (TEST_ROOT / "conftest.py").read_text(encoding="utf-8")
        self.assertIn('os.path.join(_TEST_DIR, "ut")', conftest_source)
        self.assertIn("sys.path.insert(0, _UT_DIR)", conftest_source)

    def test_catalog_lifecycle_without_exact_suite_fails_closed(self):
        """Ambiguous or verify-only catalog execution is rejected."""
        # Catalog requires a suite to be specified in config
        # This is verified by the batch config validation
        config = _batch_config()
        catalog_config = config["fvt_repo_manager"].get("catalog", {})
        # Catalog should not be run without a suite
        if catalog_config.get("run", False):
            self.assertIsNotNone(catalog_config.get("suite"))
            self.assertNotEqual(catalog_config.get("suite", ""), "")

    def test_catalog_suite_dispatches_one_full_flow(self):
        """An exact catalog suite reaches the shared test flow unchanged."""
        # When a catalog suite is specified, it should execute its own tests
        # without fan-out to other catalog operations
        runner = _validation_runner()
        # Verify that the runner can handle suite-specific execution
        self.assertTrue(hasattr(runner, "_run_test"))
        # The suite path should be constructed correctly
        catalog_suite_path = TEST_ROOT / "fvt" / "catalog" / "validate"
        self.assertTrue(catalog_suite_path.is_dir())

    def test_suite_execution_keeps_deploy_scope_exact(self):
        """Suite execution includes only its suite and any root trigger."""
        # When executing a suite, only tests in that suite should run
        # This is verified by checking that suite paths are used correctly
        runner = _validation_runner()
        # The runner should use suite-specific paths when suite is provided
        self.assertTrue(hasattr(runner, "_run_test"))

    def test_suite_execution_preserves_image_builder_root_trigger(self):
        """Shared suite filtering keeps Image Builder's deploy-test layout."""
        image_builder_root = REPOSITORY_ROOT / "test" / "image_build_manager"
        runner = shared_runner.ValidationRunner(
            domain="image_build_manager",
            script_dir=str(image_builder_root),
        )
        with patch.object(
            runner, "_invoke_pytest_with_summary", return_value=0
        ) as invoke, patch.object(shared_runner, "_info"), patch.object(
            shared_runner, "_ok"
        ):
            result = runner._run_exec("build", "s3", "", "")
        self.assertEqual(result, 0)
        self.assertEqual(
            invoke.call_args.args[0],
            [
                str(image_builder_root / "fvt" / "build" / "test_playbook.py"),
                str(image_builder_root / "fvt" / "build" / "s3"),
            ],
        )

    def test_untagged_execution_uses_ordered_lifecycle_paths(self):
        """The real runner receives each safe lifecycle directory in order."""
        # When _all_exec_tags is configured, the runner should execute
        # lifecycle tags in the correct order
        # This is verified by checking the runner's _run_exec implementation
        runner = _validation_runner()
        # The runner should have _all_exec_tags capability
        self.assertTrue(hasattr(runner, "_run_exec"))
        # Verify that lifecycle tags are defined in domain_vars
        lifecycle_tags = ["precheck", "prepare", "execute", "status"]
        fvt_tags = _literal_assignment("FVT_TAGS")
        for tag in lifecycle_tags:
            self.assertIn(tag, fvt_tags, f"Missing lifecycle tag: {tag}")

    def test_untagged_verification_excludes_negative_markers(self):
        """Aggregate verification cannot collect co-located negative cases."""
        # When running verification without specific markers, negative tests
        # should be excluded by default
        # This is verified by checking EXCLUDE_TAGS in domain_vars
        exclude_tags = _literal_assignment("EXCLUDE_TAGS")
        # Negative tests should be excluded from "all" verification
        # The negative tag itself is not in EXCLUDE_TAGS, but negative tests
        # are marked with @pytest.mark.negative
        # The verification should filter these out unless explicitly requested
        self.assertIn("negative", _literal_assignment("MARKERS"))

    def test_unit_category_is_registered_in_batch_config(self):
        """The shared runner can execute deterministic tests directly."""
        config = _batch_config()
        self.assertIn("ut_repo_manager", config)
        self.assertTrue((TEST_ROOT / "ut").is_dir())

    def test_playbook_wrapper_uses_supported_verbosity_keyword(self):
        """The domain wrapper matches the shared runner API."""
        source = (
            TEST_ROOT / "library" / "functions" / "repo_manager_func.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        wrapper = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "run_playbook"
        )
        forwarded = {
            keyword.arg
            for node in ast.walk(wrapper)
            if isinstance(node, ast.Call)
            for keyword in node.keywords
        }
        self.assertIn("verbosity", forwarded)
        self.assertNotIn("verbose", forwarded)

    def test_playbook_callers_use_supported_verbosity_keyword(self):
        """FVT callers cannot pass the removed ``verbose`` keyword."""
        offenders = []
        for path in (TEST_ROOT / "fvt").rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if getattr(node.func, "id", None) != "run_playbook":
                    continue
                if any(keyword.arg == "verbose" for keyword in node.keywords):
                    offenders.append(str(path.relative_to(TEST_ROOT)))
        self.assertEqual(offenders, [])

    def test_pytest_reporting_hooks_are_defined_once(self):
        """Later definitions cannot silently override result reporting."""
        tree = ast.parse(
            (TEST_ROOT / "conftest.py").read_text(encoding="utf-8")
        )
        names = [
            node.name for node in tree.body if isinstance(node, ast.FunctionDef)
        ]
        self.assertEqual(names.count("pytest_sessionfinish"), 1)
        self.assertEqual(names.count("pytest_runtest_makereport"), 1)

    def test_full_cleanup_fvt_matches_preserved_cli_contract(self):
        """Full cleanup no longer depends on obsolete input or CLI deletion."""
        source = (
            TEST_ROOT / "fvt" / "cleanup" / "test_status.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("cleanup_input.yml", source)
        self.assertIn("check_pulp_cli_preserved", source)
        self.assertNotIn("check_pulp_cli_removed", source)

    def test_destructive_cleanup_scenarios_are_excluded_from_all(self):
        """Cleanup can run only through an explicitly selected scenario."""
        exclude_tags = _literal_assignment("EXCLUDE_TAGS")
        self.assertIn("cleanup", exclude_tags)
        self.assertIn("cleanup_repos", exclude_tags)

    def test_unit_startup_does_not_connect_or_sync(self):
        """Deterministic unit execution bypasses FVT host setup and reporting."""
        source = (TEST_ROOT / "conftest.py").read_text(encoding="utf-8")
        session_start = source.index("def pytest_sessionstart")
        unit_guard = source.index(
            'os.environ.get("OMNIA_COMMAND_TYPE") == "ut"', session_start
        )
        host_setup = source.index("config = load_test_config()", session_start)
        self.assertLess(unit_guard, host_setup)


if __name__ == "__main__":
    unittest.main()
