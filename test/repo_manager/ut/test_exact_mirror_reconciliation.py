# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit coverage for catalog-scoped RPM exact-mirror reconciliation."""

# pylint: disable=protected-access

import json
import logging
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, call, patch

import source_loader  # noqa: F401  # pylint: disable=unused-import

from ansible.module_utils.repo_manager.pulp_commands import pulp_rpm_commands
from plugins.modules import process_rpm_config


LOGGER = logging.getLogger("repo-manager-exact-mirror-test")
REPOSITORY_NAME = "x86_64_rhel_10.0_baseos"
REPOSITORY = {
    "name": REPOSITORY_NAME,
    "package": REPOSITORY_NAME,
    "url": "https://packages.example/rhel/10/baseos/",
    "policy": "on_demand",
}


class ExactMirrorCommandTests(unittest.TestCase):
    """Verify exact-mirror command selection and Pulp response parsing."""

    @patch.object(process_rpm_config, "get_repo_version", side_effect=[1, 2])
    @patch.object(process_rpm_config, "_execute_pulp_task")
    @patch.object(
        process_rpm_config,
        "_recover_active_repository_tasks",
        return_value=(True, False, ""),
    )
    @patch.object(
        process_rpm_config,
        "_get_repository_href",
        return_value="/pulp/api/v3/repositories/rpm/rpm/repo-id/",
    )
    def test_exact_sync_uses_mirror_content_only(
        self, _href, _recover, execute_task, _version
    ):
        """Exact mode always dispatches Pulp mirror-content-only sync."""
        execute_task.return_value = (
            True,
            "/pulp/api/v3/tasks/00000000-0000-0000-0000-000000000001/",
            "",
        )
        result = process_rpm_config.sync_rpm_repository_with_monitoring(
            REPOSITORY,
            LOGGER,
            resync_repos="all",
            sync_policy="mirror_content_only",
        )
        command = execute_task.call_args.args[0]
        self.assertTrue(result[0])
        self.assertEqual(
            command[command.index("--sync-policy") + 1],
            "mirror_content_only",
        )

    @patch.object(process_rpm_config, "get_repo_version", side_effect=[1, 2])
    @patch.object(process_rpm_config, "_execute_pulp_task")
    @patch.object(
        process_rpm_config,
        "_recover_active_repository_tasks",
        return_value=(True, False, ""),
    )
    @patch.object(
        process_rpm_config,
        "_get_repository_href",
        return_value="/pulp/api/v3/repositories/rpm/rpm/repo-id/",
    )
    def test_normal_sync_does_not_change_policy(
        self, _href, _recover, execute_task, _version
    ):
        """The established additive download flow remains unchanged."""
        execute_task.return_value = (
            True,
            "/pulp/api/v3/tasks/00000000-0000-0000-0000-000000000001/",
            "",
        )
        result = process_rpm_config.sync_rpm_repository_with_monitoring(
            REPOSITORY,
            LOGGER,
            resync_repos="all",
        )
        command = execute_task.call_args.args[0]
        self.assertTrue(result[0])
        self.assertNotIn("--sync-policy", command)

    @patch.object(process_rpm_config, "_run_pulp_cli")
    def test_nested_content_summary_reports_package_delta(self, run_cli):
        """Current Pulp nested content summaries produce exact RPM deltas."""
        run_cli.return_value = SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "content_summary": {
                        "added": {
                            "rpm.package": {"count": 15},
                            "rpm.packagecategory": {"count": 1},
                        },
                        "removed": {"rpm.package": {"count": 8}},
                    }
                }
            ),
        )
        self.assertEqual(
            process_rpm_config._repository_version_metrics(
                REPOSITORY_NAME, 3, LOGGER
            ),
            (15, 8),
        )

    def test_exact_and_normal_sync_commands_remain_separate(self):
        """Exact policy is opt-in and cannot alter the default command."""
        normal = pulp_rpm_commands["sync_repository"] % (
            REPOSITORY_NAME,
            REPOSITORY_NAME,
        )
        exact = pulp_rpm_commands["sync_repository_exact_mirror"] % (
            REPOSITORY_NAME,
            REPOSITORY_NAME,
        )
        self.assertNotIn("--sync-policy", normal)
        self.assertEqual(exact[-2:], ["--sync-policy", "mirror_content_only"])

    @patch.object(process_rpm_config, "urlopen")
    @patch.object(
        process_rpm_config,
        "normalize_pulp_distribution_url",
        return_value="file:///etc",
    )
    @patch.object(
        process_rpm_config,
        "get_distribution_details",
        return_value={"base_url": "file:///etc"},
    )
    def test_repomd_validation_rejects_non_https_origin(
        self, _distribution, _normalize, open_url
    ):
        """Publication validation never follows local or custom URL schemes."""
        valid, error = process_rpm_config._validate_served_repomd(
            REPOSITORY_NAME, "https://pulp.example", LOGGER
        )
        self.assertFalse(valid)
        self.assertIn("secure HTTPS origin", error)
        open_url.assert_not_called()

    @patch.object(process_rpm_config.ssl, "create_default_context")
    @patch.object(process_rpm_config.os.path, "isfile", return_value=True)
    @patch.object(process_rpm_config, "urlopen")
    @patch.object(
        process_rpm_config,
        "normalize_pulp_distribution_url",
        return_value="https://pulp.example/pulp/content/repository",
    )
    @patch.object(
        process_rpm_config,
        "get_distribution_details",
        return_value={"base_url": "https://pulp.example/repository"},
    )
    def test_repomd_validation_rejects_xml_entities(
        self,
        _distribution,
        _normalize,
        open_url,
        _isfile,
        _ssl_context,
    ):
        """Untrusted repository metadata cannot expand XML entities."""
        response = MagicMock()
        response.status = 200
        response.read.return_value = (
            b'<!DOCTYPE repomd [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
            b"<repomd>&xxe;</repomd>"
        )
        open_url.return_value.__enter__.return_value = response

        valid, error = process_rpm_config._validate_served_repomd(
            REPOSITORY_NAME, "https://pulp.example", LOGGER
        )
        self.assertFalse(valid)
        self.assertIn("EntitiesForbidden", error)


class ExactMirrorSafetyTests(unittest.TestCase):
    """Verify fail-closed ordering, cleanup gating and rollback behavior."""

    def test_empty_catalog_repository_list_fails_closed(self):
        """A missing catalog worklist never broadens to every Pulp repository."""
        result = process_rpm_config.manage_exact_mirror_repositories(
            [], LOGGER, "https://pulp.example", run_orphan_cleanup=True
        )
        self.assertFalse(result[0])
        self.assertEqual(result[3], "not_run")

    def test_duplicate_catalog_repository_identity_fails_closed(self):
        """Duplicate repository identities are rejected before synchronization."""
        result = process_rpm_config.manage_exact_mirror_repositories(
            [REPOSITORY, dict(REPOSITORY)],
            LOGGER,
            "https://pulp.example",
            run_orphan_cleanup=True,
        )
        self.assertFalse(result[0])
        self.assertIn("Duplicate", result[2])
        self.assertEqual(result[3], "not_run")

    @patch.object(process_rpm_config, "_execute_pulp_task")
    @patch.object(process_rpm_config, "_exact_mirror_repository")
    def test_orphan_cleanup_runs_only_after_every_repo_succeeds(
        self, reconcile, execute_task
    ):
        """Aggregate orphan cleanup follows, never precedes, successful repos."""
        reconcile.return_value = (
            True,
            {"sync_status": "success", "cleanup_status": "success"},
        )
        execute_task.return_value = (True, None, "")
        result = process_rpm_config.manage_exact_mirror_repositories(
            [REPOSITORY],
            LOGGER,
            "https://pulp.example",
            run_orphan_cleanup=True,
        )
        self.assertTrue(result[0])
        self.assertEqual(result[3], "success")
        execute_task.assert_called_once()

    @patch.object(process_rpm_config, "_execute_pulp_task")
    @patch.object(process_rpm_config, "_exact_mirror_repository")
    def test_repository_failure_blocks_orphan_cleanup_and_later_repos(
        self, reconcile, execute_task
    ):
        """One failed repository stops pending work and global cleanup."""
        failed = dict(REPOSITORY)
        failed["name"] = "x86_64_rhel_10.0_baseos"
        failed["package"] = failed["name"]
        pending = dict(REPOSITORY)
        pending["name"] = "x86_64_rhel_10.0_appstream"
        pending["package"] = pending["name"]
        reconcile.return_value = (
            False,
            {
                "sync_status": "failed",
                "cleanup_status": "not_run",
                "error": "sync failed",
            },
        )
        result = process_rpm_config.manage_exact_mirror_repositories(
            [failed, pending],
            LOGGER,
            "https://pulp.example",
            run_orphan_cleanup=True,
        )
        self.assertFalse(result[0])
        self.assertEqual(result[3], "not_run")
        self.assertEqual(
            result[1]["x86_64_rhel_10.0_appstream"]["sync_status"],
            "not_run",
        )
        execute_task.assert_not_called()

    @patch.object(process_rpm_config, "_prune_superseded_repository_state")
    @patch.object(
        process_rpm_config,
        "_validate_served_repomd",
        return_value=(True, "valid"),
    )
    @patch.object(
        process_rpm_config,
        "_switch_distribution_publication",
        return_value=(True, "updated"),
    )
    @patch.object(
        process_rpm_config,
        "get_latest_publication_href",
        return_value="/pulp/api/v3/publications/rpm/rpm/new-publication/",
    )
    @patch.object(
        process_rpm_config,
        "get_repository_latest_version_href",
        return_value="/pulp/api/v3/repositories/rpm/rpm/repo-id/versions/2/",
    )
    @patch.object(process_rpm_config, "create_publication", return_value=(True, ""))
    @patch.object(
        process_rpm_config,
        "_repository_version_metrics",
        return_value=(15, 8),
    )
    @patch.object(process_rpm_config, "get_repo_version", side_effect=[1, 2])
    @patch.object(
        process_rpm_config,
        "sync_rpm_repository_with_monitoring",
        return_value=(True, REPOSITORY_NAME, True, True),
    )
    @patch.object(
        process_rpm_config,
        "_validate_exact_mirror_target",
        return_value="/pulp/api/v3/publications/rpm/rpm/old-publication/",
    )
    def test_pruning_occurs_after_replacement_validation(
        self,
        _target,
        _sync,
        _version,
        _metrics,
        _create,
        _version_href,
        _publication,
        switch,
        validate_metadata,
        prune,
    ):
        """Old state is deleted only after new metadata is served successfully."""
        success, status = process_rpm_config._exact_mirror_repository(
            REPOSITORY, "https://pulp.example", LOGGER
        )
        self.assertTrue(success)
        self.assertEqual(status["packages_removed"], 8)
        self.assertEqual(status["stale_packages_remaining"], 0)
        switch.assert_called_once()
        validate_metadata.assert_called_once()
        prune.assert_called_once()

    @patch.object(process_rpm_config, "_prune_superseded_repository_state")
    @patch.object(
        process_rpm_config,
        "_validate_served_repomd",
        return_value=(False, "bad repomd"),
    )
    @patch.object(process_rpm_config, "_switch_distribution_publication")
    @patch.object(
        process_rpm_config,
        "get_latest_publication_href",
        return_value="/pulp/api/v3/publications/rpm/rpm/new-publication/",
    )
    @patch.object(
        process_rpm_config,
        "get_repository_latest_version_href",
        return_value="/pulp/api/v3/repositories/rpm/rpm/repo-id/versions/2/",
    )
    @patch.object(process_rpm_config, "create_publication", return_value=(True, ""))
    @patch.object(
        process_rpm_config,
        "_repository_version_metrics",
        return_value=(1, 1),
    )
    @patch.object(process_rpm_config, "get_repo_version", side_effect=[1, 2])
    @patch.object(
        process_rpm_config,
        "sync_rpm_repository_with_monitoring",
        return_value=(True, REPOSITORY_NAME, True, True),
    )
    @patch.object(
        process_rpm_config,
        "_validate_exact_mirror_target",
        return_value="/pulp/api/v3/publications/rpm/rpm/old-publication/",
    )
    def test_failed_metadata_validation_restores_old_publication(
        self,
        _target,
        _sync,
        _version,
        _metrics,
        _create,
        _version_href,
        _publication,
        switch,
        _validate_metadata,
        prune,
    ):
        """A failed replacement rolls distribution back and preserves old state."""
        switch.side_effect = [(True, "updated"), (True, "restored")]
        success, status = process_rpm_config._exact_mirror_repository(
            REPOSITORY, "https://pulp.example", LOGGER
        )
        self.assertFalse(success)
        self.assertIn("bad repomd", status["error"])
        self.assertEqual(
            switch.call_args_list,
            [
                call(
                    REPOSITORY_NAME,
                    "/pulp/api/v3/publications/rpm/rpm/new-publication/",
                    LOGGER,
                ),
                call(
                    REPOSITORY_NAME,
                    "/pulp/api/v3/publications/rpm/rpm/old-publication/",
                    LOGGER,
                ),
            ],
        )
        prune.assert_not_called()

    @patch.object(process_rpm_config, "_execute_pulp_task")
    @patch.object(
        process_rpm_config,
        "_list_repository_versions",
        return_value=[0, 1, 2, 3],
    )
    @patch.object(process_rpm_config, "_list_publications")
    def test_pruning_preserves_empty_and_current_versions(
        self, publications, _versions, execute_task
    ):
        """Cleanup removes only superseded publications and nonzero versions."""
        current = (
            "/pulp/api/v3/publications/rpm/rpm/"
            "00000000-0000-0000-0000-000000000001/"
        )
        old = (
            "/pulp/api/v3/publications/rpm/rpm/"
            "00000000-0000-0000-0000-000000000002/"
        )
        publications.return_value = [
            {"pulp_href": old},
            {"pulp_href": current},
        ]
        execute_task.return_value = (True, None, "")
        process_rpm_config._prune_superseded_repository_state(
            REPOSITORY_NAME, current, 3, LOGGER
        )
        commands = [item.args[0] for item in execute_task.call_args_list]
        self.assertIn(old, commands[0])
        self.assertIn("2", commands[1])
        self.assertIn("1", commands[2])
        self.assertFalse(any(command[-1] in {"0", "3"} for command in commands[1:]))


if __name__ == "__main__":
    unittest.main()
