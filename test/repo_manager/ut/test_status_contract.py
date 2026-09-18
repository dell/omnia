# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Tests for multi-context status aggregation and atomic publication."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml

from source_loader import REPO_MANAGER_ROOT

from ansible.module_utils.repo_manager.repository_status_builder import (
    build_terminal_context_status,
    merge_context_status,
    merge_version_mapping,
    summarize_execution_contexts,
)
from plugins.modules import generate_local_repo_access


CONTEXTS = [
    {
        "context_id": "rhel_10.0",
        "os_type": "rhel",
        "os_version": "10.0",
        "architectures": ["x86_64", "aarch64"],
    },
    {
        "context_id": "rhel_10.2",
        "os_type": "rhel",
        "os_version": "10.2",
        "architectures": ["aarch64"],
    },
]


class StatusBuilderTests(unittest.TestCase):
    """Cover terminal, in-progress and failed multi-version status."""

    def test_context_summary_contains_only_public_stable_fields(self):
        """Internal catalog data cannot leak through execution contexts."""
        contexts = [{**CONTEXTS[0], "catalog_files": ["secret.json"]}]
        self.assertEqual(summarize_execution_contexts(contexts), [CONTEXTS[0]])

    def test_success_requires_every_selected_context(self):
        """A partially completed multi-version run remains in progress."""
        status, aggregate = build_terminal_context_status(
            CONTEXTS,
            [{"context_id": "rhel_10.0", "status": "success"}],
            "success",
        )
        self.assertEqual(status, {"10.0": "success", "10.2": "pending"})
        self.assertEqual(aggregate, "in_progress")

    def test_failure_keeps_later_context_pending(self):
        """A failed active version cannot make an unexecuted version successful."""
        status, aggregate = build_terminal_context_status(
            CONTEXTS,
            [{"context_id": "rhel_10.0", "status": "failed"}],
            "failed",
        )
        self.assertEqual(status, {"10.0": "failed", "10.2": "pending"})
        self.assertEqual(aggregate, "failed")

    def test_first_context_resets_stale_selected_version_status(self):
        """A new pass cannot retain success from an earlier selected version."""
        previous = {
            "overall_status_by_version": {"10.0": "success", "10.2": "success"}
        }
        status, aggregate = merge_context_status(
            previous, CONTEXTS, "10.0", "success"
        )
        self.assertEqual(status, {"10.0": "success", "10.2": "pending"})
        self.assertEqual(aggregate, "in_progress")

    def test_version_mapping_removes_unselected_versions(self):
        """Changing catalog selection removes obsolete version output."""
        merged = merge_version_mapping(
            {"repositories": {"9.6": {}, "10.0": {"old": True}}},
            "repositories",
            "10.2",
            {"new": True},
            selected_versions=["10.0", "10.2"],
        )
        self.assertEqual(
            merged,
            {"10.0": {"old": True}, "10.2": {"new": True}},
        )


class StatusPublicationTests(unittest.TestCase):
    """Verify fail-closed content and interrupted atomic replacement."""

    def test_failed_status_contains_no_consumable_repository_urls(self):
        """A failed run publishes empty repository maps and legacy URLs."""
        generator = generate_local_repo_access.LocalRepoAccessGenerator.__new__(
            generate_local_repo_access.LocalRepoAccessGenerator
        )
        generator.execution_contexts = CONTEXTS
        generator.execution_results = [
            {"context_id": "rhel_10.0", "status": "failed"}
        ]
        generator.missing_rpm_repositories_by_version = {}
        generator.repo_config = "partial"
        generator.pulp_server_port = 2225
        generator.certs_dir = "/safe/certs"
        content, rpm_count, file_count = generator.generate_failed_yaml_content()
        data = yaml.safe_load(content)
        self.assertEqual(data["overall_status"], "failed")
        self.assertEqual(data["repositories"]["10.0"]["x86_64"], {})
        self.assertEqual(data["repositories"]["10.2"]["aarch64"], {})
        self.assertEqual(data["offline_tarball_path"], "")
        self.assertEqual((rpm_count, file_count), (0, 0))

    def test_atomic_write_preserves_previous_status_on_replace_failure(self):
        """An interrupted publication retains the last complete public status."""
        with tempfile.TemporaryDirectory() as work_dir:
            output = Path(work_dir) / "repo_status.yml"
            output.write_text("overall_status: success\n", encoding="utf-8")
            generator = generate_local_repo_access.LocalRepoAccessGenerator.__new__(
                generate_local_repo_access.LocalRepoAccessGenerator
            )
            generator.output_path = str(output)
            with patch.object(
                generate_local_repo_access.os,
                "replace",
                side_effect=OSError("simulated interruption"),
            ):
                with self.assertRaises(OSError):
                    generator.write_yaml("overall_status: failed\n")
            self.assertEqual(
                output.read_text(encoding="utf-8"),
                "overall_status: success\n",
            )
            self.assertEqual(list(Path(work_dir).glob(".repo_status.yml.*")), [])

    def test_removed_file_repos_by_version_field_is_not_reintroduced(self):
        """The current output contract owns only the common file_repos field."""
        source = (
            REPO_MANAGER_ROOT / "plugins" / "modules" /
            "generate_local_repo_access.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("file_repos_by_version", source)


if __name__ == "__main__":
    unittest.main()
