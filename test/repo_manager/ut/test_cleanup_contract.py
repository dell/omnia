# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Regression tests for selective and full cleanup contracts."""

# pylint: disable=protected-access

import csv
import json
import logging
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from source_loader import REPO_MANAGER_ROOT

from plugins.modules import pulp_cleanup


LOGGER = logging.getLogger("repo-manager-cleanup-test")


def _write_mirror_index(base_path, version, packages):
    path = (
        Path(base_path) / "rhel" / version / "mirror_status" /
        "pulp_mirror_index.json"
    )
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({
            "MirrorIndex": {
                "schema_version": 2,
                "timestamp": "",
                "summary": {},
                "packages": packages,
            }
        }),
        encoding="utf-8",
    )
    return path


def _entry(name, artifact_type, version, arch, repo_name=""):
    return {
        "package_name": name,
        "type": artifact_type,
        "version": version,
        "arch": arch,
        "hash": f"{version}-{arch}-{name}",
        "status": "mirrored",
        "repo_name": repo_name,
    }


class CleanupContextTests(unittest.TestCase):
    """Cover exact version/architecture scope across Cases 1-6."""

    def test_cases_one_to_four_use_target_version_log(self):
        """Single-context RPM cleanup logs under its exact minor version."""
        contexts = [
            {"os_version": "10.0", "architectures": ["x86_64", "aarch64"]},
            {"os_version": "10.2", "architectures": ["x86_64", "aarch64"]},
        ]
        targets = (
            "x86_64_rhel_10.0_baseos",
            "x86_64_rhel_10.2_baseos",
            "aarch64_rhel_10.0_baseos",
            "aarch64_rhel_10.2_baseos",
        )
        with tempfile.TemporaryDirectory() as work_dir:
            for target in targets:
                with self.subTest(target=target):
                    version = target.split("_rhel_", 1)[1].split("_", 1)[0]
                    actual = pulp_cleanup.resolve_cleanup_log_dir(
                        work_dir, "rhel", "10.0", contexts, [target], [], []
                    )
                    self.assertEqual(
                        actual,
                        str(Path(work_dir) / "rhel" / version / "cleanup"),
                    )

    def test_dual_architecture_shared_artifact_uses_version_log(self):
        """A shared artifact within one version stays version-scoped."""
        contexts = [{
            "os_version": "10.0",
            "architectures": ["x86_64", "aarch64"],
        }]
        with tempfile.TemporaryDirectory() as work_dir:
            actual = pulp_cleanup.resolve_cleanup_log_dir(
                work_dir,
                "rhel",
                "10.0",
                contexts,
                [],
                ["docker.io/library/busybox:1.37"],
                [],
            )
            self.assertEqual(
                actual, str(Path(work_dir) / "rhel" / "10.0" / "cleanup")
            )

    def test_cross_version_cleanup_uses_aggregate_log(self):
        """Shared or multi-version cleanup cannot be attributed to one version."""
        contexts = [
            {"os_version": "10.0", "architectures": ["x86_64"]},
            {"os_version": "10.2", "architectures": ["aarch64"]},
        ]
        with tempfile.TemporaryDirectory() as work_dir:
            container_log = pulp_cleanup.resolve_cleanup_log_dir(
                work_dir,
                "rhel",
                "10.0",
                contexts,
                [],
                ["docker.io/library/busybox:1.37"],
                [],
            )
            rpm_log = pulp_cleanup.resolve_cleanup_log_dir(
                work_dir,
                "rhel",
                "10.0",
                contexts,
                [
                    "x86_64_rhel_10.0_baseos",
                    "aarch64_rhel_10.2_baseos",
                ],
                [],
                [],
            )
            expected = str(Path(work_dir) / "rhel" / "cleanup")
            self.assertEqual(container_log, expected)
            self.assertEqual(rpm_log, expected)

    def test_repository_removal_is_version_and_architecture_scoped(self):
        """An exact RPM cleanup cannot erase a near context match."""
        with tempfile.TemporaryDirectory() as work_dir:
            first = _write_mirror_index(work_dir, "10.0", {
                "x86-baseos": _entry("bash", "rpm", "1", "x86_64", "baseos"),
                "arm-baseos": _entry("bash", "rpm", "1", "aarch64", "baseos"),
            })
            second = _write_mirror_index(work_dir, "10.2", {
                "arm-baseos": _entry("bash", "rpm", "2", "aarch64", "baseos"),
            })
            removed = pulp_cleanup.remove_repo_from_mirror_index(
                "x86_64_rhel_10.0_baseos",
                work_dir,
                "rhel",
                "10.0",
                LOGGER,
            )
            self.assertEqual(removed, 1)
            self.assertEqual(
                set(json.loads(first.read_text(encoding="utf-8"))[
                    "MirrorIndex"
                ]["packages"]),
                {"arm-baseos"},
            )
            self.assertEqual(
                set(json.loads(second.read_text(encoding="utf-8"))[
                    "MirrorIndex"
                ]["packages"]),
                {"arm-baseos"},
            )

    def test_shared_container_is_invalidated_in_every_owning_context(self):
        """An exact shared tag is removed from every matching context only."""
        with tempfile.TemporaryDirectory() as work_dir:
            indexes = [
                _write_mirror_index(work_dir, version, {
                    f"image-{version}": _entry(
                        "docker.io/library/busybox", "image", "1.37", arch
                    ),
                    f"other-{version}": _entry(
                        "docker.io/library/nginx", "image", "1.27", arch
                    ),
                })
                for version, arch in (
                    ("10.0", "x86_64"),
                    ("10.2", "aarch64"),
                )
            ]
            removed = pulp_cleanup.remove_artifact_from_mirror_index(
                "docker.io/library/busybox:1.37",
                "image",
                work_dir,
                "rhel",
                "10.0",
                LOGGER,
            )
            self.assertEqual(removed, 2)
            for index_path in indexes:
                packages = json.loads(index_path.read_text(encoding="utf-8"))[
                    "MirrorIndex"
                ]["packages"]
                self.assertEqual(len(packages), 1)
                self.assertTrue(next(iter(packages)).startswith("other-"))

    def test_group_status_update_is_version_scoped(self):
        """Marking one context partial does not contaminate another version."""
        with tempfile.TemporaryDirectory() as work_dir:
            status_files = []
            for version in ("10.0", "10.2"):
                status_path = (
                    Path(work_dir) / "rhel" / version / "x86_64" /
                    "groups_status.csv"
                )
                status_path.parent.mkdir(parents=True)
                status_path.write_text(
                    "name,status\nbaseos_group,success\n", encoding="utf-8"
                )
                status_files.append(status_path)
            pulp_cleanup.mark_software_partial(
                {"x86_64": ["baseos_group"]},
                work_dir,
                LOGGER,
                "repository",
                "rhel",
                "10.0",
            )
            statuses = []
            for status_path in status_files:
                with status_path.open(encoding="utf-8") as stream:
                    statuses.append(next(csv.DictReader(stream))["status"])
            self.assertEqual(statuses, ["partial", "success"])

    def test_bare_file_request_expands_to_exact_context_matches(self):
        """A bare file identity excludes prefix/suffix near matches."""
        repositories = [
            "x86_64_rhel_10.0_gitexample",
            "aarch64_rhel_10.2_gitexample",
            "x86_64_rhel_10.0_gitexample-tools",
        ]
        expanded, errors = pulp_cleanup.expand_cleanup_file_requests(
            ["example"], repositories
        )
        self.assertEqual(expanded, repositories[:2])
        self.assertEqual(errors, [])

    def test_pinned_python_request_expands_to_exact_versions(self):
        """Pinned Python cleanup retains package-version identity."""
        repositories = [
            "x86_64_rhel_10.0_pip_modulecffi==1.17.1",
            "aarch64_rhel_10.0_pip_modulecffi==1.17.1",
            "x86_64_rhel_10.2_pip_modulecffi==1.17.1",
            "x86_64_rhel_10.0_pip_modulecffi==1.17.2",
        ]
        expanded, errors = pulp_cleanup.expand_cleanup_file_requests(
            ["cffi==1.17.1"], repositories
        )
        self.assertEqual(expanded, repositories[:3])
        self.assertEqual(errors, [])

    def test_malformed_python_cleanup_identity_is_rejected(self):
        """Malformed version syntax cannot become a cleanup target."""
        malformed = "x86_64_rhel_10.0_pip_modulecffi===1.17.1"
        expanded, errors = pulp_cleanup.expand_cleanup_file_requests(
            [malformed], [malformed]
        )
        self.assertEqual(expanded, [])
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["type"], "pip_module")

    def test_content_directory_cleanup_preserves_other_contexts(self):
        """Local cleanup removes only the selected OS/version/architecture path."""
        with tempfile.TemporaryDirectory() as work_dir:
            store = Path(work_dir) / "store"
            selected = (
                store / "offline_repo" / "cluster" / "x86_64" / "rhel" /
                "10.0" / "pip_module" / "cffi==1.17.1"
            )
            retained = (
                store / "offline_repo" / "cluster" / "aarch64" / "rhel" /
                "10.2" / "pip_module" / "cffi==1.17.1"
            )
            selected.mkdir(parents=True)
            retained.mkdir(parents=True)
            (selected / "cffi.whl").write_text("selected", encoding="utf-8")
            (retained / "cffi.whl").write_text("retained", encoding="utf-8")
            result = pulp_cleanup.cleanup_content_directory(
                "cffi==1.17.1",
                "pip_module",
                str(store),
                LOGGER,
                arch="x86_64",
                os_type="rhel",
                os_version="10.0",
            )
            self.assertEqual(result["status"], "Success")
            self.assertTrue(result["changed"])
            self.assertFalse(selected.exists())
            self.assertTrue(retained.exists())


class CleanupStateTests(unittest.TestCase):
    """Verify true no-op reporting and safe dependency ordering."""

    def test_pulp_cli_uses_fixed_system_path(self):
        """Selective cleanup cannot select an alternate executable implicitly."""
        with patch.object(pulp_cleanup, "run_cmd") as run_cmd:
            run_cmd.return_value = {"rc": 0, "stdout": "", "stderr": ""}
            pulp_cleanup.run_pulp(["status"], LOGGER)
        run_cmd.assert_called_once_with(
            ["/usr/local/bin/pulp", "status"], LOGGER, timeout=300
        )

    def test_orphan_timeout_exceeds_general_command_timeout(self):
        """Storage reclamation has a dedicated long-running timeout."""
        self.assertGreater(
            pulp_cleanup.PULP_ORPHAN_CLEANUP_TIMEOUT,
            pulp_cleanup.PULP_COMMAND_TIMEOUT,
        )

    def test_already_absent_object_is_unchanged(self):
        """Repeated cleanup reports success without a false change."""
        with patch.object(
            pulp_cleanup, "_pulp_object_exists", return_value=False
        ):
            success, message, changed = pulp_cleanup._delete_named_object(
                "rpm", "repository", "repo", LOGGER
            )
        self.assertTrue(success)
        self.assertIn("already absent", message)
        self.assertFalse(changed)

    def test_not_found_query_is_confirmed_absence(self):
        """Only an explicit Pulp not-found response proves absence."""
        with patch.object(
            pulp_cleanup,
            "run_pulp",
            return_value={"rc": 1, "stdout": "", "stderr": "Not found"},
        ):
            exists = pulp_cleanup._pulp_object_exists(
                "rpm", "repository", "repo", Mock()
            )
        self.assertIs(exists, False)

    def test_operational_query_error_is_unknown(self):
        """Authentication or transport failures never become absence."""
        with patch.object(
            pulp_cleanup,
            "run_pulp",
            return_value={"rc": 1, "stdout": "", "stderr": "Unauthorized"},
        ):
            exists = pulp_cleanup._pulp_object_exists(
                "rpm", "repository", "repo", Mock()
            )
        self.assertIsNone(exists)

    def test_unknown_object_state_does_not_trigger_deletion(self):
        """Cleanup fails closed when object presence cannot be established."""
        with patch.object(
            pulp_cleanup, "_pulp_object_exists", return_value=None
        ), patch.object(pulp_cleanup, "run_pulp") as run_pulp:
            success, message, changed = pulp_cleanup._delete_named_object(
                "rpm", "repository", "repo", LOGGER
            )
        self.assertFalse(success)
        self.assertIn("Unable to check", message)
        self.assertFalse(changed)
        run_pulp.assert_not_called()

    def test_verified_object_deletion_is_changed(self):
        """A confirmed present-to-absent transition reports changed."""
        with patch.object(
            pulp_cleanup,
            "_pulp_object_exists",
            side_effect=[True, False],
        ), patch.object(
            pulp_cleanup,
            "run_pulp",
            return_value={"rc": 0, "stdout": "", "stderr": ""},
        ):
            success, _message, changed = pulp_cleanup._delete_named_object(
                "rpm", "repository", "repo", LOGGER
            )
        self.assertTrue(success)
        self.assertTrue(changed)

    def test_repo_status_invalidation_is_idempotent(self):
        """The first cleanup removes stale consumer state; the second is a no-op."""
        with tempfile.TemporaryDirectory() as work_dir:
            repo_status = (
                Path(work_dir) / "output" / "project_default" /
                "repo_status.yml"
            )
            repo_status.parent.mkdir(parents=True)
            repo_status.write_text("overall_status: success\n", encoding="utf-8")
            self.assertTrue(
                pulp_cleanup.invalidate_repo_status(
                    str(repo_status), work_dir, LOGGER
                )
            )
            self.assertFalse(
                pulp_cleanup.invalidate_repo_status(
                    str(repo_status), work_dir, LOGGER
                )
            )

    def test_repo_status_outside_runtime_root_is_rejected(self):
        """A cleanup path cannot escape the configured runtime root."""
        with tempfile.TemporaryDirectory() as work_dir:
            outside = Path(work_dir) / "not-output" / "repo_status.yml"
            outside.parent.mkdir()
            outside.write_text("overall_status: success\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                pulp_cleanup.invalidate_repo_status(
                    str(outside), work_dir, LOGGER
                )
            self.assertTrue(outside.exists())

    def test_pulp_repo_stanza_removal_is_idempotent(self):
        """A DNF stanza is changed once and remains absent on rerun."""
        with tempfile.TemporaryDirectory() as work_dir:
            repo_file = Path(work_dir) / "pulp.repo"
            repo_file.write_text(
                "[x86_64_rhel_10.0_baseos]\nbaseurl=https://pulp/baseos\n",
                encoding="utf-8",
            )
            success, changed = pulp_cleanup.remove_repos_from_pulp_repo_file(
                ["x86_64_rhel_10.0_baseos"], str(repo_file), LOGGER
            )
            self.assertTrue(success)
            self.assertTrue(changed)
            success, changed = pulp_cleanup.remove_repos_from_pulp_repo_file(
                ["x86_64_rhel_10.0_baseos"], str(repo_file), LOGGER
            )
            self.assertTrue(success)
            self.assertFalse(changed)

    def test_full_cleanup_invalidates_consumers_before_stopping_pulp(self):
        """Public and DNF consumer state is removed before endpoint teardown."""
        cleanup_playbook = (
            REPO_MANAGER_ROOT / "playbooks" / "cleanup" / "cleanup_pulp.yml"
        ).read_text(encoding="utf-8")
        invalidate_position = cleanup_playbook.index(
            "- name: Invalidate Pulp consumer state before removing the endpoint"
        )
        stop_position = cleanup_playbook.index("- name: Stop pulp service")
        verify_cli_position = cleanup_playbook.index(
            "- name: Verify preserved Pulp CLI command chain"
        )
        self.assertLess(invalidate_position, stop_position)
        self.assertLess(invalidate_position, verify_cli_position)

    def test_configuration_cleanup_invalidates_before_stopping_pulp(self):
        """Configuration-only cleanup follows the same dependency order."""
        cleanup_playbook = (
            REPO_MANAGER_ROOT / "playbooks" / "cleanup" / "cleanup_repos.yml"
        ).read_text(encoding="utf-8")
        invalidate_position = cleanup_playbook.index(
            "- name: Invalidate Pulp consumer state before configuration cleanup"
        )
        stop_position = cleanup_playbook.index(
            "- name: Stop Pulp systemd service"
        )
        self.assertLess(invalidate_position, stop_position)

    def test_full_cleanup_preserves_managed_cli_chain(self):
        """Cleanup removes CLI configuration but retains launcher and backend."""
        cleanup_playbook = (
            REPO_MANAGER_ROOT / "playbooks" / "cleanup" / "cleanup_pulp.yml"
        ).read_text(encoding="utf-8")
        cleanup_vars = (
            REPO_MANAGER_ROOT / "vars" / "cleanup_pulp_vars.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("Verify preserved Pulp CLI command chain", cleanup_playbook)
        self.assertIn("managed Pulp CLI launcher", cleanup_vars)
        self.assertNotIn("{{ pulp_cli_executable }}", cleanup_vars.split(
            "pulp_cli_config_files:", 1
        )[1].split("credential_files_to_cleanup:", 1)[0])

    def test_credential_cleanup_default_and_preserve_values_are_documented(self):
        """Default deletion and explicit preservation spellings remain stable."""
        cleanup_playbook = (
            REPO_MANAGER_ROOT / "playbooks" / "cleanup" / "cleanup_pulp.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("['false', 'no', '0']", cleanup_playbook)
        self.assertIn("else true", cleanup_playbook)


if __name__ == "__main__":
    unittest.main()
