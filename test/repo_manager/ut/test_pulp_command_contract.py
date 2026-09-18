# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Regression tests for the centralized, shell-free Pulp CLI boundary."""

import re
import unittest

import yaml

from source_loader import REPO_MANAGER_ROOT  # pylint: disable=wrong-import-position

from ansible.module_utils.repo_manager import config
from ansible.module_utils.repo_manager.pulp_commands import (
    build_container_remote_command,
    build_pulp_entity_command,
    build_pulp_task_list_command,
    command_argv,
    pulp_common_commands,
    pulp_container_commands,
    pulp_file_commands,
    pulp_python_commands,
    pulp_rpm_commands,
    pulp_task_commands,
)
from ansible.module_utils.repo_manager.repo_paths import PULP_CLI_EXECUTABLE


class PulpCommandBuilderTests(unittest.TestCase):
    """Verify command parity, allowlists and argument isolation."""

    def test_template_returns_fresh_structured_argv(self):
        """Templates use the configured executable and never share argv."""
        first = pulp_rpm_commands["show_repository"] % "repo"
        second = pulp_rpm_commands["show_repository"] % "repo"

        self.assertEqual(
            first,
            [PULP_CLI_EXECUTABLE, "rpm", "repository", "show", "--name", "repo"],
        )
        self.assertIsNot(first, second)

    def test_file_path_with_spaces_remains_one_argument(self):
        """File paths containing spaces cannot alter command structure."""
        command = pulp_file_commands["content_upload"] % (
            "repo", "/tmp/file with spaces.tar", "artifact.tar",
        )
        self.assertEqual(
            command[-3:],
            ["/tmp/file with spaces.tar", "--relative-path", "artifact.tar"],
        )

    def test_container_password_cannot_add_arguments(self):
        """Shell punctuation in a password remains one opaque argument."""
        password = "secret'; touch /tmp/not-executed; #"
        command = build_container_remote_command(
            "create",
            name="remote",
            url="https://registry.example",
            upstream_name="library/image",
            policy="on_demand",
            include_tags=["1.0"],
            username="user",
            password=password,
        )
        self.assertEqual(command[command.index("--password") + 1], password)
        self.assertEqual(command.count(password), 1)

    def test_task_filters_are_built_centrally(self):
        """Exact task correlation retains the established CLI ordering."""
        command = build_pulp_task_list_command(
            reserved_resource="/pulp/api/v3/repositories/rpm/rpm/id/",
            states=("waiting", "running", "canceling"),
            limit=100,
            ordering="pulp_created",
        )
        self.assertEqual(command.count("--state-in"), 3)
        self.assertEqual(command[-2:], ["--ordering", "pulp_created"])

    def test_task_state_is_allowlisted(self):
        """An unknown task state cannot become dynamic Pulp grammar."""
        with self.assertRaises(ValueError):
            build_pulp_task_list_command(states=("completed;rm",))

    def test_cleanup_tokens_are_allowlisted(self):
        """Cleanup accepts only known Pulp plugins, resources and actions."""
        command = build_pulp_entity_command(
            "rpm", "repository", "destroy", name="repo"
        )
        self.assertEqual(
            command[1:],
            ["rpm", "repository", "destroy", "--name", "repo"],
        )
        with self.assertRaises(ValueError):
            build_pulp_entity_command(
                "rpm;touch", "repository", "destroy", name="repo"
            )

    def test_name_and_href_are_mutually_exclusive(self):
        """An entity command cannot contain two conflicting identities."""
        with self.assertRaises(ValueError):
            build_pulp_entity_command(
                "rpm", "repository", "show", name="repo", href="/repo/1/"
            )

    def test_every_static_template_is_structured(self):
        """Every static template is immutable and begins with one executable."""
        groups = (
            pulp_common_commands,
            pulp_task_commands,
            pulp_file_commands,
            pulp_python_commands,
            pulp_container_commands,
            pulp_rpm_commands,
        )
        for command_group in groups:
            for template in command_group.values():
                with self.subTest(template=template):
                    self.assertIsInstance(template, tuple)
                    self.assertEqual(template[0], PULP_CLI_EXECUTABLE)

    def test_executable_override_changes_only_argv_zero(self):
        """A configured executable override preserves command grammar."""
        command = command_argv(
            pulp_rpm_commands["list_distributions"],
            executable="/opt/pulp/bin/pulp",
        )
        self.assertEqual(command[0], "/opt/pulp/bin/pulp")
        self.assertEqual(
            command[1:],
            ["rpm", "distribution", "list", "--limit", "1000"],
        )

    def test_compatibility_exports_remain_valid(self):
        """Established config imports remain available to callers."""
        self.assertTrue(all(isinstance(name, str) for name in config.__all__))
        self.assertIs(config.pulp_rpm_commands, pulp_rpm_commands)


class PulpCommandSourceBoundaryTests(unittest.TestCase):
    """Prevent distributed Pulp command construction from returning."""

    def test_pulp_commands_are_not_defined_at_python_call_sites(self):
        """Production Python callers cannot reintroduce Pulp grammar."""
        central_file = (
            REPO_MANAGER_ROOT / "plugins" / "module_utils" /
            "repo_manager" / "pulp_commands.py"
        )
        patterns = (
            re.compile(r"\[\s*['\"]pulp['\"]"),
            re.compile(
                r"=\s*f?['\"]pulp\s+"
                r"(?:rpm|file|python|container|task|show|status|orphan)\b"
            ),
            re.compile(
                r"\[\s*PULP_CLI_EXECUTABLE\s*,\s*['\"]"
                r"(?:rpm|file|python|container|task|show|status|orphan)['\"]"
            ),
        )
        violations = []
        for source_file in (REPO_MANAGER_ROOT / "plugins").rglob("*.py"):
            if source_file == central_file:
                continue
            if "module_utils/catalog" in source_file.as_posix():
                continue
            content = source_file.read_text(encoding="utf-8")
            if any(pattern.search(content) for pattern in patterns):
                violations.append(str(source_file.relative_to(REPO_MANAGER_ROOT)))
        self.assertEqual(violations, [])

    def test_yaml_common_commands_have_one_definition(self):
        """YAML owns only the status and version command suffixes."""
        command_file = REPO_MANAGER_ROOT / "vars" / "pulp_cli_commands.yml"
        commands = yaml.safe_load(command_file.read_text(encoding="utf-8"))
        self.assertEqual(
            commands["pulp_cli_commands"]["common"],
            {"status": ["status"], "version": ["--version"]},
        )

    def test_pulp_command_module_does_not_own_dnf(self):
        """DNF command construction remains outside the Pulp boundary."""
        content = (
            REPO_MANAGER_ROOT / "plugins" / "module_utils" /
            "repo_manager" / "pulp_commands.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("DNF_COMMANDS", content)
        self.assertNotIn('"dnf"', content)


if __name__ == "__main__":
    unittest.main()
