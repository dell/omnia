# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Tri-state Pulp query and File lifecycle regression tests."""

# pylint: disable=protected-access

import logging
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import source_loader  # noqa: F401  # pylint: disable=unused-import

from ansible.module_utils.repo_manager import download_common
from ansible.module_utils.repo_manager import pulp_object_state


LOGGER = logging.getLogger("repo-manager-pulp-state-test")


class PulpObjectStateTests(unittest.TestCase):
    """Only explicit not-found state can authorize object creation."""

    def test_successful_json_query_is_present(self):
        """A successful structured response returns present with its data."""
        executor = Mock(return_value={
            "returncode": 0,
            "success": True,
            "stdout": {"name": "repo"},
            "stderr": None,
        })
        present, details = pulp_object_state.query_pulp_object(
            ["pulp", "file", "repository", "show"], LOGGER, executor
        )
        self.assertIs(present, True)
        self.assertEqual(details, {"name": "repo"})

    def test_explicit_not_found_query_is_absent(self):
        """A recognized Pulp not-found diagnostic returns confirmed absence."""
        executor = Mock(return_value={
            "returncode": 1,
            "success": False,
            "stdout": None,
            "stderr": "404 object not found",
        })
        present, details = pulp_object_state.query_pulp_object(
            ["pulp", "file", "repository", "show"], LOGGER, executor
        )
        self.assertIs(present, False)
        self.assertIsNone(details)

    def test_operational_query_failure_is_unknown(self):
        """Authentication and transport errors never become absence."""
        executor = Mock(return_value={
            "returncode": 1,
            "success": False,
            "stdout": None,
            "stderr": "authentication failed",
        })
        present, details = pulp_object_state.query_pulp_object(
            ["pulp", "file", "repository", "show"], LOGGER, executor
        )
        self.assertIsNone(present)
        self.assertIsNone(details)

    def test_unknown_file_repository_state_causes_no_mutation(self):
        """File processing stops before upload when repository state is unknown."""
        with tempfile.TemporaryDirectory() as work_dir:
            artifact = Path(work_dir) / "artifact.tar.gz"
            artifact.write_bytes(b"data")
            with patch.object(
                download_common, "execute_command", return_value=None
            ) as execute:
                result = download_common.process_file_without_download(
                    "x86_64_rhel_10.0_tarballartifact",
                    "artifact.tar.gz",
                    "artifact.tar.gz",
                    "offline_repo/cluster/x86_64/rhel/10.0/tarball/artifact",
                    "x86_64_rhel_10.0_tarballartifact",
                    "https://example.invalid/artifact.tar.gz",
                    str(artifact),
                    LOGGER,
                )
        self.assertEqual(result, "Failed")
        execute.assert_called_once()

    def test_file_content_reuses_digest_without_upload(self):
        """Existing exact File content is associated without byte upload."""
        with tempfile.TemporaryDirectory() as work_dir:
            artifact = Path(work_dir) / "artifact.tar.gz"
            artifact.write_bytes(b"shared-file-content")
            responses = [
                {
                    "returncode": 0,
                    "success": True,
                    "stdout": [{"relative_path": artifact.name}],
                },
                {"returncode": 0},
                {
                    "returncode": 0,
                    "success": True,
                    "stdout": {"latest_version_href": "/versions/2/"},
                },
                {
                    "returncode": 0,
                    "success": True,
                    "stdout": [{"relative_path": artifact.name}],
                },
            ]
            with patch.object(
                download_common, "execute_command", side_effect=responses
            ) as execute:
                result = download_common._reconcile_file_content(
                    "repo", str(artifact), artifact.name, LOGGER
                )
        self.assertTrue(result)
        commands = [call.args[0] for call in execute.call_args_list]
        self.assertIn("modify", commands[1])
        self.assertNotIn("upload", commands[1])

    def test_python_content_reuses_digest_without_upload(self):
        """Existing Python content is associated by digest without re-upload."""
        with tempfile.TemporaryDirectory() as work_dir:
            artifact = Path(work_dir) / "example-1.0-py3-none-any.whl"
            artifact.write_bytes(b"shared-python-content")
            responses = [
                {
                    "returncode": 0,
                    "success": True,
                    "stdout": [{"filename": artifact.name}],
                },
                {"returncode": 0},
                {
                    "returncode": 0,
                    "success": True,
                    "stdout": {"latest_version_href": "/versions/3/"},
                },
                {
                    "returncode": 0,
                    "success": True,
                    "stdout": [{"filename": artifact.name}],
                },
            ]
            with patch.object(
                download_common, "execute_command", side_effect=responses
            ) as execute:
                result = download_common._reconcile_python_content(
                    "repo", str(artifact), LOGGER
                )
        self.assertTrue(result)
        commands = [call.args[0] for call in execute.call_args_list]
        self.assertIn("modify", commands[1])
        self.assertNotIn("upload", commands[1])

    def test_unknown_content_query_causes_no_mutation(self):
        """An unknown global content read blocks upload and association."""
        with tempfile.TemporaryDirectory() as work_dir:
            artifact = Path(work_dir) / "artifact.tar.gz"
            artifact.write_bytes(b"data")
            with patch.object(
                download_common, "execute_command", return_value=None
            ) as execute:
                result = download_common._reconcile_file_content(
                    "repo", str(artifact), artifact.name, LOGGER
                )
        self.assertFalse(result)
        execute.assert_called_once()

    def test_distribution_accepts_expected_repository_binding(self):
        """A reconciled endpoint is ready only with its intended repository."""
        responses = [
            {
                "returncode": 0,
                "success": True,
                "stdout": {"pulp_href": "/repositories/file/expected/"},
            },
            {
                "returncode": 1,
                "success": False,
                "stderr": "404 distribution does not exist",
            },
            True,
            {
                "returncode": 0,
                "success": True,
                "stdout": {"repository": "/repositories/file/expected/"},
            },
        ]
        with patch.object(
                download_common, "execute_command", side_effect=responses):
            result = download_common._reconcile_pulp_distribution(
                ["pulp", "file", "distribution", "show"],
                ["pulp", "file", "distribution", "create"],
                ["pulp", "file", "distribution", "update"],
                "File distribution expected",
                LOGGER,
                ["pulp", "file", "repository", "show"],
            )
        self.assertTrue(result)

    def test_distribution_rejects_wrong_repository_binding(self):
        """A same-name distribution pointing elsewhere is not marked ready."""
        responses = [
            {
                "returncode": 0,
                "success": True,
                "stdout": {"pulp_href": "/repositories/file/expected/"},
            },
            {
                "returncode": 0,
                "success": True,
                "stdout": {"repository": "/repositories/file/stale/"},
            },
            True,
            {
                "returncode": 0,
                "success": True,
                "stdout": {"repository": "/repositories/file/stale/"},
            },
        ]
        with patch.object(
                download_common, "execute_command", side_effect=responses):
            result = download_common._reconcile_pulp_distribution(
                ["pulp", "file", "distribution", "show"],
                ["pulp", "file", "distribution", "create"],
                ["pulp", "file", "distribution", "update"],
                "File distribution expected",
                LOGGER,
                ["pulp", "file", "repository", "show"],
            )
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
