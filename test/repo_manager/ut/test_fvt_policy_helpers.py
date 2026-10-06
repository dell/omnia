# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.

"""Deterministic contracts for Repo Manager's live policy helpers."""

# pylint: disable=wrong-import-position

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
TEST_ROOT = REPOSITORY_ROOT / "test" / "repo_manager"
SHARED_PLUGIN_ROOT = REPOSITORY_ROOT / "test" / "plugins"

for import_root in (TEST_ROOT, SHARED_PLUGIN_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from library.functions import repo_manager_func  # noqa: E402


def _result(return_code=0, stdout="", stderr=""):
    """Build the command result shape returned by run_on_host."""
    return SimpleNamespace(rc=return_code, stdout=stdout, stderr=stderr)


class FvtPolicyHelperTests(unittest.TestCase):
    """Keep live checks aligned with Repo Manager's configuration contract."""

    @patch.object(repo_manager_func, "_cmd_file_exists")
    @patch.object(repo_manager_func, "run_on_host")
    @patch.object(
        repo_manager_func, "_get_input_path", return_value="/opt/omnia/test-input"
    )
    def test_repo_caching_uses_lowercase_global_key(
            self, _input_path, run_on_host, file_exists):
        """Per-repo fallback reads caching_policy and defaults to true."""
        file_exists.return_value = _result(stdout="exists\n")

        run_on_host.side_effect = [
            _result(stdout="not_set\n"),
            _result(stdout="true\n"),
        ]

        result = repo_manager_func.check_repo_caching(object(), "baseos")

        self.assertTrue(result["success"])
        self.assertTrue(result["caching"])
        self.assertEqual(result["source"], "global")
        self.assertEqual(run_on_host.call_count, 2)
        global_command = run_on_host.call_args_list[1].args[1]
        self.assertIn("config.get('caching_policy', True)", global_command)

    @patch.object(repo_manager_func, "_cmd_file_exists")
    @patch.object(repo_manager_func, "run_on_host")
    @patch.object(
        repo_manager_func, "_get_input_path", return_value="/opt/omnia/test-input"
    )
    def test_global_caching_uses_lowercase_key(
            self, _input_path, run_on_host, file_exists):
        """Global helper follows the production caching_policy spelling."""
        file_exists.return_value = _result(stdout="exists\n")

        def command_result(_host, command):
            self.assertIn("config.get('caching_policy', True)", command)
            return _result(stdout="true\n")

        run_on_host.side_effect = command_result

        result = repo_manager_func.check_global_caching_policy(object())

        self.assertTrue(result["success"])
        self.assertTrue(result["caching_policy"])

    @patch.object(repo_manager_func, "get_configured_repos")
    @patch.object(repo_manager_func, "get_repo_status_contexts")
    def test_configured_repository_contexts_cover_every_selected_context(
            self, status_contexts, configured_repos):
        """Configured policy checks retain their exact version and architecture."""
        status_contexts.return_value = {
            "success": True,
            "details": "",
            "error": "",
            "contexts": [
                ("rhel", "10.0", "x86_64"),
                ("rhel", "10.2", "aarch64"),
            ],
        }
        configured_repos.side_effect = [
            {"success": True, "details": "", "error": "", "repos": ["baseos"]},
            {"success": True, "details": "", "error": "", "repos": ["epel"]},
        ]

        result = repo_manager_func.get_configured_repo_contexts(object())

        self.assertTrue(result["success"])
        self.assertEqual(
            result["repositories"],
            [
                {"name": "baseos", "architecture": "x86_64", "os_version": "10.0"},
                {"name": "epel", "architecture": "aarch64", "os_version": "10.2"},
            ],
        )
        self.assertEqual(
            configured_repos.call_args_list[1].args[1:], ("aarch64", "10.2")
        )

    @patch.object(repo_manager_func, "get_deployed_repos")
    @patch.object(repo_manager_func, "get_repo_status_contexts")
    def test_deployed_repository_contexts_fail_closed(
            self, status_contexts, deployed_repos):
        """A missing selected context cannot be hidden by another valid context."""
        status_contexts.return_value = {
            "success": True,
            "details": "",
            "error": "",
            "contexts": [
                ("rhel", "10.0", "x86_64"),
                ("rhel", "10.2", "x86_64"),
            ],
        }
        deployed_repos.side_effect = [
            {"success": True, "details": "", "error": "", "repos": ["baseos"]},
            {
                "success": False,
                "details": "10.2 repository mapping is invalid",
                "error": "invalid mapping",
                "repos": [],
            },
        ]

        result = repo_manager_func.get_deployed_repo_contexts(object())

        self.assertFalse(result["success"])
        self.assertEqual(result["repositories"], [])
        self.assertEqual(result["error"], "invalid mapping")

    @patch.object(repo_manager_func, "_get_pulp_certs_dir", return_value="/certs")
    @patch.object(repo_manager_func, "run_on_host")
    @patch.object(repo_manager_func, "_read_repo_status")
    def test_content_access_uses_literal_curl_status_token(
            self, read_status, run_on_host, _certs_dir):
        """The curl status token survives Python command formatting unchanged."""
        read_status.return_value = {
            "success": True,
            "details": {
                "repositories": {
                    "10.2": {
                        "aarch64": {
                            "baseos": {
                                "url": "https://pulp.example/content/baseos/"
                            }
                        }
                    }
                }
            },
            "error": "",
        }
        run_on_host.return_value = _result(stdout="200")

        result = repo_manager_func.check_pulp_content_accessible(object())

        self.assertTrue(result["success"])
        command = run_on_host.call_args.args[1]
        self.assertIn("--write-out '%{http_code}'", command)
        self.assertIn("/repodata/repomd.xml", command)
        self.assertIn("--cacert /certs/pulp_webserver.crt", command)

    @patch.object(repo_manager_func, "load_test_config", return_value={})
    @patch.object(repo_manager_func, "run_on_host")
    def test_pulp_repository_list_counts_json_entries(
            self, run_on_host, _load_test_config):
        """Pulp's JSON list output is counted without relying on table labels."""
        run_on_host.return_value = _result(
            stdout='[{"name": "baseos"}, {"name": "appstream"}]'
        )

        result = repo_manager_func.check_pulp_cli_repository_list(object())

        self.assertTrue(result["success"])
        self.assertIn("2 RPM repositories", result["details"])

    @patch.object(repo_manager_func, "load_test_config", return_value={})
    @patch.object(repo_manager_func, "run_on_host")
    def test_pulp_repository_list_rejects_non_list_json(
            self, run_on_host, _load_test_config):
        """A valid but incompatible Pulp response fails closed."""
        run_on_host.return_value = _result(stdout='{"name": "baseos"}')

        result = repo_manager_func.check_pulp_cli_repository_list(object())

        self.assertFalse(result["success"])
        self.assertIn("did not return a JSON list", result["error"])

    @patch.object(repo_manager_func, "_read_repo_status")
    def test_deployed_repos_come_from_catalog_status(self, read_repo_status):
        """Policy integration checks only catalog-selected repositories."""
        read_repo_status.return_value = {
            "success": True,
            "details": {
                "repositories": {
                    "10.0": {
                        "x86_64": {
                            "baseos": {"url": "https://pulp/baseos/"},
                            "appstream": {"url": "https://pulp/appstream/"},
                        }
                    }
                }
            },
            "error": "",
        }

        result = repo_manager_func.get_deployed_repos(object())

        self.assertTrue(result["success"])
        self.assertEqual(result["repos"], ["baseos", "appstream"])

    @patch.object(repo_manager_func, "_cmd_file_exists")
    @patch.object(repo_manager_func, "run_on_host")
    @patch.object(
        repo_manager_func, "_get_input_path", return_value="/opt/omnia/test-input"
    )
    def test_repository_source_type_uses_configured_url(
            self, _input_path, run_on_host, file_exists):
        """Source-type checks distinguish URL and subscription repositories."""
        file_exists.return_value = _result(stdout="exists\n")
        run_on_host.return_value = _result(stdout="url\n")

        result = repo_manager_func.check_repo_source_type(object(), "epel")

        self.assertTrue(result["success"])
        self.assertEqual(result["source_type"], "url")
        command = run_on_host.call_args.args[1]
        self.assertIn("additional_repos", command)
        self.assertIn("user_repos", command)


if __name__ == "__main__":
    unittest.main()
